import base64
import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EnhancedBankReconciliation(models.Model):
    _name = "enhanced.bank.reconciliation"
    _description = "Enhanced Bank Reconciliation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Bank Journal",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        required=True,
        check_company=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many(
        "enhanced.bank.reconciliation.line",
        "reconciliation_id",
        string="Bank Lines",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In Progress"), ("done", "Done")],
        string="State",
        default="draft",
        tracking=True,
        required=True,
    )
    total_line_count = fields.Integer(compute="_compute_summary")
    matched_line_count = fields.Integer(compute="_compute_summary")
    unmatched_line_count = fields.Integer(compute="_compute_summary")
    suggested_line_count = fields.Integer(compute="_compute_summary")
    exception_line_count = fields.Integer(compute="_compute_summary")
    matched_amount = fields.Monetary(
        string="Matched Amount",
        currency_field="currency_id",
        compute="_compute_summary",
    )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq.next_by_code("enhanced.bank.reconciliation") or _("New")
        return super().create(vals_list)

    @api.depends("line_ids.state", "line_ids.amount")
    def _compute_summary(self):
        for record in self:
            record.total_line_count = len(record.line_ids)
            record.matched_line_count = len(record.line_ids.filtered(lambda l: l.state == "matched"))
            record.unmatched_line_count = len(record.line_ids.filtered(lambda l: l.state in ("draft", "exception")))
            record.suggested_line_count = len(record.line_ids.filtered(lambda l: l.state == "suggested"))
            record.exception_line_count = len(record.line_ids.filtered(lambda l: l.state == "exception"))
            record.matched_amount = sum(record.line_ids.filtered(lambda l: l.state == "matched").mapped("amount"))

    def action_run_auto_match(self):
        for record in self:
            record.line_ids.action_auto_match()
            record.state = "in_progress"
        return True

    def action_mark_done(self):
        for record in self:
            if record.line_ids.filtered(lambda l: l.state in ("draft", "exception")):
                raise UserError(_("Tum satirlar eslesmeden veya cozumlulugu belirlenmeden kayit kapatilamaz."))
            record.state = "done"
        return True

    def action_open_unmatched_lines(self):
        self.ensure_one()
        return {
            "name": _("Unmatched Bank Lines"),
            "type": "ir.actions.act_window",
            "res_model": "enhanced.bank.reconciliation.line",
            "view_mode": "list,form",
            "domain": [("reconciliation_id", "=", self.id), ("state", "in", ("draft", "exception"))],
            "context": {"default_reconciliation_id": self.id},
        }


class EnhancedBankReconciliationLine(models.Model):
    _name = "enhanced.bank.reconciliation.line"
    _description = "Enhanced Bank Reconciliation Line"
    _order = "date desc, id desc"
    _check_company_auto = True

    reconciliation_id = fields.Many2one(
        "enhanced.bank.reconciliation",
        string="Reconciliation",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        related="reconciliation_id.company_id",
        store=True,
        readonly=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        related="reconciliation_id.journal_id",
        store=True,
        readonly=True,
    )
    date = fields.Date(string="Date", required=True)
    description = fields.Char(string="Description", required=True)
    reference = fields.Char(string="Reference")
    amount = fields.Monetary(string="Amount", currency_field="currency_id", required=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    partner_id = fields.Many2one("res.partner", string="Partner", check_company=True)
    state = fields.Selection(
        [("draft", "Draft"), ("suggested", "Suggested"), ("matched", "Matched"), ("exception", "Exception")],
        string="State",
        default="draft",
        required=True,
    )
    matched_move_line_id = fields.Many2one(
        "account.move.line",
        string="Matched Move Line",
        check_company=True,
        domain="[('company_id', '=', company_id), ('reconciled', '=', False)]",
    )
    suggested_move_line_id = fields.Many2one(
        "account.move.line",
        string="Suggested Move Line",
        check_company=True,
        domain="[('company_id', '=', company_id), ('reconciled', '=', False)]",
    )
    exception_flag = fields.Boolean(
        string="Exception",
        compute="_compute_exception_flag",
        store=True,
    )
    exception_note = fields.Char(string="Exception Note")

    @api.depends("amount", "state")
    def _compute_exception_flag(self):
        threshold = 10000.0
        for line in self:
            line.exception_flag = line.state != "matched" and abs(line.amount) >= threshold

    @api.constrains("amount")
    def _check_amount(self):
        for line in self:
            if not line.amount:
                raise ValidationError(_("Banka hareket tutari sifir olamaz."))

    def _get_matching_domain(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("account_id.account_type", "in", ("asset_receivable", "liability_payable")),
        ]
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        return domain

    def _find_match_candidate(self):
        self.ensure_one()
        AccountMoveLine = self.env["account.move.line"]
        domain = self._get_matching_domain()
        exact_amount = abs(self.amount)
        if self.reference:
            by_ref = AccountMoveLine.search(
                domain
                + [
                    "|",
                    ("move_name", "ilike", self.reference),
                    ("move_id.ref", "ilike", self.reference),
                ],
                limit=1,
            )
            if by_ref and self.currency_id.is_zero(abs(abs(by_ref.amount_residual_currency or by_ref.amount_residual) - exact_amount)):
                return by_ref
        if self.partner_id:
            by_partner = AccountMoveLine.search(domain + [("partner_id", "=", self.partner_id.id)], limit=10)
            matched = by_partner.filtered(
                lambda line: self.currency_id.is_zero(abs(abs(line.amount_residual_currency or line.amount_residual) - exact_amount))
            )
            if len(matched) == 1:
                return matched[0]
        by_amount = AccountMoveLine.search(domain, limit=20)
        matched = by_amount.filtered(
            lambda line: self.currency_id.is_zero(abs(abs(line.amount_residual_currency or line.amount_residual) - exact_amount))
        )
        return matched[0] if len(matched) == 1 else False

    def action_auto_match(self):
        for line in self:
            candidate = line._find_match_candidate()
            if candidate:
                line.suggested_move_line_id = candidate
                line.state = "suggested"
                line.exception_note = False
            else:
                line.state = "exception" if line.exception_flag else "draft"
                line.exception_note = _("Otomatik eslesme bulunamadi.")
        return True

    def action_match(self):
        for line in self:
            candidate = line.matched_move_line_id or line.suggested_move_line_id
            if not candidate:
                raise UserError(_("Eslesecek hareket satiri secilmelidir."))
            line.matched_move_line_id = candidate
            line.state = "matched"
            line.exception_note = False
        return True

    def action_unmatch(self):
        self.write(
            {
                "matched_move_line_id": False,
                "suggested_move_line_id": False,
                "state": "draft",
                "exception_note": False,
            }
        )
        return True

    @api.model
    def cron_mark_bank_exceptions(self):
        lines = self.search([("state", "!=", "matched"), ("amount", "!=", 0.0)])
        for line in lines:
            if line.exception_flag:
                line.write({"state": "exception", "exception_note": _("Yuksek tutarli eslesmemis banka hareketi.")})


class EnhancedBankImportMixin(models.AbstractModel):
    _name = "enhanced.bank.import.mixin"
    _description = "Enhanced Bank Import Helper"

    def _parse_bank_csv(self, file_data):
        decoded = base64.b64decode(file_data)
        stream = io.StringIO(decoded.decode("utf-8-sig"))
        reader = csv.DictReader(stream)
        rows = []
        required = {"date", "description", "reference", "amount", "currency", "partner"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise UserError(_("CSV basliklari date, description, reference, amount, currency, partner olmalidir."))
        for row in reader:
            rows.append(row)
        return rows
