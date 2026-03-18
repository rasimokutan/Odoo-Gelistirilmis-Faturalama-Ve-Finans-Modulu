from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    finance_overdue_days = fields.Integer(
        string="Overdue Days",
        compute="_compute_finance_state",
        store=True,
    )
    finance_duplicate_vendor_ref = fields.Boolean(
        string="Duplicate Vendor Reference",
        compute="_compute_finance_state",
    )
    finance_high_risk_warning = fields.Boolean(
        string="High Risk Warning",
        compute="_compute_finance_state",
    )
    finance_partner_overdue_amount = fields.Monetary(
        string="Partner Overdue Amount",
        currency_field="company_currency_id",
        compute="_compute_finance_state",
    )
    finance_alert_message = fields.Text(
        string="Finance Alert",
        compute="_compute_finance_state",
    )
    finance_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Default Analytic Account",
        check_company=True,
    )
    finance_followup_log_ids = fields.One2many(
        "enhanced.finance.followup.log",
        "invoice_id",
        string="Follow-up Logs",
    )
    finance_followup_count = fields.Integer(
        string="Follow-up Count",
        compute="_compute_finance_state",
    )
    finance_budget_warning = fields.Text(
        string="Budget Warning",
        compute="_compute_budget_warning",
    )
    finance_last_followup_level = fields.Selection(
        [("level_1", "1. Hatirlatma"), ("level_2", "2. Hatirlatma"), ("final", "Son Uyari")],
        string="Last Follow-up Level",
        compute="_compute_finance_state",
    )

    @api.depends(
        "invoice_date_due",
        "payment_state",
        "partner_id",
        "state",
        "ref",
        "amount_total",
        "finance_followup_log_ids",
    )
    def _compute_finance_state(self):
        today = fields.Date.context_today(self)
        for move in self:
            overdue_days = 0
            if move.invoice_date_due and move.payment_state in ("not_paid", "partial", "in_payment") and move.invoice_date_due < today:
                overdue_days = (today - move.invoice_date_due).days
            duplicate = False
            if move.move_type in ("in_invoice", "in_refund") and move.partner_id and move.ref:
                duplicate = bool(
                    self.search_count(
                        [
                            ("id", "!=", move.id),
                            ("company_id", "=", move.company_id.id),
                            ("partner_id", "=", move.partner_id.id),
                            ("move_type", "in", ("in_invoice", "in_refund")),
                            ("ref", "=", move.ref),
                            ("state", "!=", "cancel"),
                        ]
                    )
                )
            last_log = move.finance_followup_log_ids.sorted("sent_date")[-1:] if move.finance_followup_log_ids else self.env["enhanced.finance.followup.log"]
            move.finance_overdue_days = overdue_days
            move.finance_duplicate_vendor_ref = duplicate
            move.finance_high_risk_warning = move.partner_id.finance_risk_level == "high"
            move.finance_partner_overdue_amount = move.partner_id.finance_overdue_amount
            move.finance_followup_count = len(move.finance_followup_log_ids)
            move.finance_last_followup_level = last_log.reminder_level if last_log else False
            alerts = []
            if move.partner_id.finance_risk_level == "high":
                alerts.append(_("Partner finans riski yuksek."))
            if duplicate:
                alerts.append(_("Ayni tedarikci referansi baska bir kayitta bulundu."))
            if move.partner_id.finance_overdue_amount >= 10000:
                alerts.append(_("Partnerin yuksek tutarda gecikmis borcu/alacagi var."))
            if overdue_days:
                alerts.append(_("Bu belge %s gundur gecikmede.") % overdue_days)
            move.finance_alert_message = " ".join(alerts)

    @api.depends("invoice_line_ids.analytic_distribution", "invoice_line_ids.account_id", "company_id")
    def _compute_budget_warning(self):
        BudgetLine = self.env["enhanced.finance.budget.line"]
        for move in self:
            warnings = []
            analytic_account_ids = set()
            for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                if line.analytic_distribution:
                    analytic_account_ids.update(int(acc_id) for acc_id in line.analytic_distribution.keys())
            if analytic_account_ids:
                budget_lines = BudgetLine.search(
                    [
                        ("budget_id.state", "=", "confirmed"),
                        ("company_id", "=", move.company_id.id),
                        ("analytic_account_id", "in", list(analytic_account_ids)),
                    ]
                )
                for budget_line in budget_lines:
                    if budget_line.is_over_budget:
                        warnings.append(
                            _("%(analytic)s icin butce asimi var (%(practical).2f / %(planned).2f).")
                            % {
                                "analytic": budget_line.analytic_account_id.display_name,
                                "practical": budget_line.practical_amount,
                                "planned": budget_line.planned_amount,
                            }
                        )
            move.finance_budget_warning = "\n".join(warnings)

    @api.onchange("partner_id")
    def _onchange_partner_finance_risk(self):
        if self.partner_id.finance_risk_level == "high":
            return {
                "warning": {
                    "title": _("High Financial Risk"),
                    "message": _(
                        "Secili partner yuksek risk seviyesinde. Gecikmis bakiyeleri ve takip gecmisini kontrol edin."
                    ),
                }
            }
        if self.partner_id.finance_overdue_amount >= 10000:
            return {
                "warning": {
                    "title": _("Overdue Exposure"),
                    "message": _(
                        "Partnerin yuksek tutarda gecikmis bakiyesi bulunuyor."
                    ),
                }
            }
        return {}

    @api.onchange("ref", "partner_id", "move_type")
    def _onchange_duplicate_vendor_ref(self):
        if self.move_type not in ("in_invoice", "in_refund") or not self.partner_id or not self.ref:
            return {}
        duplicates = self.search(
            [
                ("id", "!=", self.id),
                ("company_id", "=", self.company_id.id or self.env.company.id),
                ("partner_id", "=", self.partner_id.id),
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("ref", "=", self.ref),
                ("state", "!=", "cancel"),
            ],
            limit=1,
        )
        if duplicates:
            return {
                "warning": {
                    "title": _("Duplicate Vendor Reference"),
                    "message": _("Bu tedarikci referansi daha once %s kaydinda kullanilmis.") % duplicates.display_name,
                }
            }
        return {}

    @api.constrains("amount_total", "move_type")
    def _check_negative_totals(self):
        for move in self:
            if move.move_type in ("out_invoice", "in_invoice", "out_receipt", "in_receipt") and move.amount_total < 0:
                raise ValidationError(_("Negatif toplam tutar standart fatura/bill kayitlarinda kabul edilmez."))

    def action_apply_default_analytic(self):
        for move in self:
            if not move.finance_analytic_account_id:
                raise UserError(_("Varsayilan analytic account secmelisiniz."))
            distribution = {str(move.finance_analytic_account_id.id): 100}
            move.invoice_line_ids.filtered(lambda l: not l.display_type).write(
                {"analytic_distribution": distribution}
            )
        return True

    def action_open_followup_wizard(self):
        self.ensure_one()
        return {
            "name": _("Send Finance Follow-up"),
            "type": "ir.actions.act_window",
            "res_model": "enhanced.finance.followup.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.commercial_partner_id.id,
                "default_invoice_ids": self.ids,
            },
        }

    def action_post(self):
        for move in self:
            if move.move_type != "entry":
                if not move.invoice_date_due:
                    raise UserError(_("Fatura veya bill post edilmeden once vade tarihi doldurulmalidir."))
                if move.amount_total < 0:
                    raise UserError(_("Negatif toplamli belge post edilemez."))
            if move.partner_id.finance_risk_level == "high":
                move.message_post(body=_("Post oncesi finansal risk uyarisi: partner yuksek risk seviyesinde."))
            if move.finance_budget_warning:
                move.message_post(body=move.finance_budget_warning.replace("\n", "<br/>"))
        result = super().action_post()
        return result
