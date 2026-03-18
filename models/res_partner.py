from collections import defaultdict

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    finance_total_receivable = fields.Monetary(
        string="Toplam Alacak",
        currency_field="company_currency_id",
        compute="_compute_finance_summary",
    )
    finance_total_payable = fields.Monetary(
        string="Toplam Borc",
        currency_field="company_currency_id",
        compute="_compute_finance_summary",
    )
    finance_overdue_amount = fields.Monetary(
        string="Gecikmis Tutar",
        currency_field="company_currency_id",
        compute="_compute_finance_summary",
    )
    finance_overdue_count = fields.Integer(
        string="Gecikmis Fatura Sayisi",
        compute="_compute_finance_summary",
    )
    finance_age_0_30 = fields.Monetary(
        string="0-30 Gun",
        currency_field="company_currency_id",
        compute="_compute_finance_summary",
    )
    finance_age_31_60 = fields.Monetary(
        string="31-60 Gun",
        currency_field="company_currency_id",
        compute="_compute_finance_summary",
    )
    finance_age_61_90 = fields.Monetary(
        string="61-90 Gun",
        currency_field="company_currency_id",
        compute="_compute_finance_summary",
    )
    finance_age_90_plus = fields.Monetary(
        string="90+ Gun",
        currency_field="company_currency_id",
        compute="_compute_finance_summary",
    )
    finance_paid_on_time_rate = fields.Float(
        string="Zamaninda Odeme Orani",
        compute="_compute_finance_summary",
    )
    finance_risk_score = fields.Integer(
        string="Risk Puani",
        compute="_compute_finance_summary",
    )
    finance_risk_level = fields.Selection(
        [("low", "Dusuk"), ("medium", "Orta"), ("high", "Yuksek")],
        string="Risk Seviyesi",
        compute="_compute_finance_summary",
    )
    finance_followup_log_ids = fields.One2many(
        "enhanced.finance.followup.log",
        "partner_id",
        string="Finans Takipleri",
    )
    finance_followup_count = fields.Integer(
        string="Takip Sayisi",
        compute="_compute_finance_summary",
    )
    finance_summary_note = fields.Text(
        string="Finans Ozeti",
        compute="_compute_finance_summary",
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        string="Sirket Para Birimi",
        compute="_compute_company_currency_id",
    )

    def _compute_company_currency_id(self):
        for partner in self:
            partner.company_currency_id = (
                partner.company_id.currency_id or self.env.company.currency_id
            )

    def _get_finance_partner_domain(self):
        commercial_partner = self.commercial_partner_id or self
        return [("partner_id", "child_of", commercial_partner.id)]

    @api.depends("company_id")
    def _compute_finance_summary(self):
        today = fields.Date.context_today(self)
        for partner in self:
            company = partner.company_id or self.env.company
            move_domain = [
                ("state", "=", "posted"),
                ("company_id", "=", company.id),
                ("payment_state", "in", ("not_paid", "partial", "in_payment", "paid")),
            ] + partner._get_finance_partner_domain()
            invoices = self.env["account.move"].search(
                move_domain
                + [("move_type", "in", ("out_invoice", "out_refund", "out_receipt", "in_invoice", "in_refund", "in_receipt"))]
            )
            unpaid_customer = invoices.filtered(
                lambda m: m.is_sale_document(include_receipts=True)
                and m.payment_state in ("not_paid", "partial", "in_payment")
            )
            unpaid_vendor = invoices.filtered(
                lambda m: m.is_purchase_document(include_receipts=True)
                and m.payment_state in ("not_paid", "partial", "in_payment")
            )
            overdue = invoices.filtered(
                lambda m: m.payment_state in ("not_paid", "partial", "in_payment")
                and m.invoice_date_due
                and m.invoice_date_due < today
            )
            aging = defaultdict(float)
            for move in overdue:
                amount = abs(move.amount_residual_signed)
                overdue_days = (today - move.invoice_date_due).days
                if overdue_days <= 30:
                    aging["0_30"] += amount
                elif overdue_days <= 60:
                    aging["31_60"] += amount
                elif overdue_days <= 90:
                    aging["61_90"] += amount
                else:
                    aging["90_plus"] += amount

            paid_customer = invoices.filtered(
                lambda m: m.is_sale_document(include_receipts=True)
                and m.payment_state == "paid"
                and m.invoice_date_due
            )
            paid_on_time = 0
            for move in paid_customer:
                payment_dates = move.line_ids.mapped("matched_debit_ids.max_date") + move.line_ids.mapped("matched_credit_ids.max_date")
                payment_dates = [date for date in payment_dates if date]
                if payment_dates and max(payment_dates) <= move.invoice_date_due:
                    paid_on_time += 1
            total_paid = len(paid_customer)
            on_time_rate = (paid_on_time / total_paid) * 100 if total_paid else 100.0

            overdue_total = sum(abs(move.amount_residual_signed) for move in overdue)
            overdue_count = len(overdue)
            followup_count = self.env["enhanced.finance.followup.log"].search_count(
                [("partner_id", "=", partner.commercial_partner_id.id), ("company_id", "=", company.id)]
            )
            score = min(
                100,
                int(min(overdue_count * 12, 36) + min(overdue_total / 1000.0 * 8, 40) + max(0, 24 - (on_time_rate / 100.0) * 24)),
            )
            if score >= 70:
                risk_level = "high"
            elif score >= 35:
                risk_level = "medium"
            else:
                risk_level = "low"

            partner.finance_total_receivable = sum(abs(m.amount_residual_signed) for m in unpaid_customer)
            partner.finance_total_payable = sum(abs(m.amount_residual_signed) for m in unpaid_vendor)
            partner.finance_overdue_amount = overdue_total
            partner.finance_overdue_count = overdue_count
            partner.finance_age_0_30 = aging["0_30"]
            partner.finance_age_31_60 = aging["31_60"]
            partner.finance_age_61_90 = aging["61_90"]
            partner.finance_age_90_plus = aging["90_plus"]
            partner.finance_paid_on_time_rate = on_time_rate
            partner.finance_risk_score = score
            partner.finance_risk_level = risk_level
            partner.finance_followup_count = followup_count
            partner.finance_summary_note = _(
                "Acik alacak: %(recv).2f | Acik borc: %(pay).2f | Geciken tutar: %(over).2f | Zamaninda odeme: %(rate).1f%%"
            ) % {
                "recv": partner.finance_total_receivable,
                "pay": partner.finance_total_payable,
                "over": overdue_total,
                "rate": on_time_rate,
            }

    def action_open_finance_followups(self):
        self.ensure_one()
        action = self.env.ref(
            "enhanced_invoicing_accounting.action_enhanced_finance_followup"
        ).read()[0]
        action["domain"] = [("partner_id", "=", self.commercial_partner_id.id)]
        action["context"] = {"default_partner_id": self.commercial_partner_id.id}
        return action

    def action_open_partner_aging_report(self):
        self.ensure_one()
        action = self.env.ref(
            "enhanced_invoicing_accounting.action_partner_aging_report"
        ).read()[0]
        action["domain"] = [("partner_id", "=", self.commercial_partner_id.id)]
        return action
