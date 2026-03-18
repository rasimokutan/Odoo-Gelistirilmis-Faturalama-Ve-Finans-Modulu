from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EnhancedFinanceBudget(models.Model):
    _name = "enhanced.finance.budget"
    _description = "Gelismis Finans Butcesi"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_from desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Butce Adi", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Sirket",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    date_from = fields.Date(string="Baslangic Tarihi", required=True)
    date_to = fields.Date(string="Bitis Tarihi", required=True)
    state = fields.Selection(
        [("draft", "Taslak"), ("confirmed", "Onayli"), ("closed", "Kapali")],
        string="Durum",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        "enhanced.finance.budget.line",
        "budget_id",
        string="Butce Satirlari",
    )
    over_budget_count = fields.Integer(compute="_compute_budget_summary")
    total_planned_amount = fields.Monetary(
        string="Planlanan",
        currency_field="currency_id",
        compute="_compute_budget_summary",
    )
    total_practical_amount = fields.Monetary(
        string="Gerceklesen",
        currency_field="currency_id",
        compute="_compute_budget_summary",
    )

    @api.depends("line_ids.planned_amount", "line_ids.practical_amount", "line_ids.is_over_budget")
    def _compute_budget_summary(self):
        for budget in self:
            budget.over_budget_count = len(budget.line_ids.filtered("is_over_budget"))
            budget.total_planned_amount = sum(budget.line_ids.mapped("planned_amount"))
            budget.total_practical_amount = sum(budget.line_ids.mapped("practical_amount"))

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for budget in self:
            if budget.date_from > budget.date_to:
                raise ValidationError(_("Butce baslangic tarihi bitis tarihinden buyuk olamaz."))

    def action_confirm(self):
        for budget in self:
            if not budget.line_ids:
                raise UserError(_("Onaylamak icin en az bir butce satiri gereklidir."))
            budget.state = "confirmed"
        return True

    def action_reset_draft(self):
        self.write({"state": "draft"})
        return True

    def action_close(self):
        self.write({"state": "closed"})
        return True


class EnhancedFinanceBudgetLine(models.Model):
    _name = "enhanced.finance.budget.line"
    _description = "Gelismis Finans Butce Satiri"
    _order = "budget_id, id"
    _check_company_auto = True

    budget_id = fields.Many2one(
        "enhanced.finance.budget",
        string="Butce",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        related="budget_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="budget_id.currency_id",
        store=True,
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analitik Hesap",
        required=True,
        check_company=True,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Hesap",
        required=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    planned_amount = fields.Monetary(
        string="Planlanan Tutar",
        currency_field="currency_id",
        required=True,
    )
    practical_amount = fields.Monetary(
        string="Gerceklesen Tutar",
        currency_field="currency_id",
        compute="_compute_practical_amount",
        store=False,
    )
    achievement_rate = fields.Float(
        string="Gerceklesme Orani",
        compute="_compute_practical_amount",
        store=False,
    )
    is_over_budget = fields.Boolean(
        string="Butce Asimi",
        compute="_compute_practical_amount",
    )
    warning_message = fields.Char(
        string="Uyari",
        compute="_compute_practical_amount",
    )

    @api.depends(
        "planned_amount",
        "analytic_account_id",
        "account_id",
        "budget_id.date_from",
        "budget_id.date_to",
        "budget_id.state",
    )
    def _compute_practical_amount(self):
        AnalyticLine = self.env["account.analytic.line"]
        for line in self:
            practical = 0.0
            if line.analytic_account_id and line.account_id:
                practical = abs(
                    sum(
                        AnalyticLine.search(
                            [
                                ("company_id", "=", line.company_id.id),
                                ("account_id", "=", line.analytic_account_id.id),
                                ("general_account_id", "=", line.account_id.id),
                                ("date", ">=", line.budget_id.date_from),
                                ("date", "<=", line.budget_id.date_to),
                            ]
                        ).mapped("amount")
                    )
                )
            line.practical_amount = practical
            line.achievement_rate = (practical / line.planned_amount * 100.0) if line.planned_amount else 0.0
            line.is_over_budget = practical > line.planned_amount if line.planned_amount else False
            line.warning_message = (
                _("Butce asildi.") if line.is_over_budget else False
            )

    @api.constrains("planned_amount")
    def _check_planned_amount(self):
        for line in self:
            if line.planned_amount <= 0:
                raise ValidationError(_("Planlanan butce tutari sifirdan buyuk olmalidir."))

    @api.model
    def cron_budget_overrun_notice(self):
        lines = self.search([("budget_id.state", "=", "confirmed")])
        for line in lines.filtered("is_over_budget"):
            line.budget_id.message_post(
                body=_(
                    "%(analytic)s / %(account)s butce satiri asim durumunda."
                )
                % {
                    "analytic": line.analytic_account_id.display_name,
                    "account": line.account_id.display_name,
                }
            )
