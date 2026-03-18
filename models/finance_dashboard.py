from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class EnhancedFinanceDashboard(models.TransientModel):
    _name = "enhanced.finance.dashboard"
    _description = "Gelismis Finans Panosu"

    company_id = fields.Many2one(
        "res.company",
        string="Sirket",
        default=lambda self: self.env.company,
        required=True,
    )
    date_from = fields.Date(
        string="Baslangic",
        default=lambda self: fields.Date.context_today(self) - relativedelta(months=1),
    )
    date_to = fields.Date(
        string="Bitis",
        default=fields.Date.context_today,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=False,
    )
    total_receivable = fields.Monetary(currency_field="currency_id", compute="_compute_dashboard")
    total_payable = fields.Monetary(currency_field="currency_id", compute="_compute_dashboard")
    overdue_receivable = fields.Monetary(currency_field="currency_id", compute="_compute_dashboard")
    overdue_payable = fields.Monetary(currency_field="currency_id", compute="_compute_dashboard")
    draft_invoices = fields.Integer(compute="_compute_dashboard")
    unpaid_customer_invoices = fields.Integer(compute="_compute_dashboard")
    unpaid_vendor_bills = fields.Integer(compute="_compute_dashboard")
    matched_bank_lines = fields.Integer(compute="_compute_dashboard")
    unmatched_bank_lines = fields.Integer(compute="_compute_dashboard")

    @api.depends("company_id", "date_from", "date_to")
    def _compute_dashboard(self):
        today = fields.Date.context_today(self)
        for dashboard in self:
            move_domain = [
                ("company_id", "=", dashboard.company_id.id),
                ("move_type", "in", ("out_invoice", "out_receipt", "in_invoice", "in_receipt")),
            ]
            if dashboard.date_from:
                move_domain.append(("invoice_date", ">=", dashboard.date_from))
            if dashboard.date_to:
                move_domain.append(("invoice_date", "<=", dashboard.date_to))
            posted = self.env["account.move"].search(move_domain + [("state", "=", "posted")])
            receivables = posted.filtered(
                lambda m: m.is_sale_document(include_receipts=True) and m.payment_state in ("not_paid", "partial", "in_payment")
            )
            payables = posted.filtered(
                lambda m: m.is_purchase_document(include_receipts=True) and m.payment_state in ("not_paid", "partial", "in_payment")
            )
            dashboard.total_receivable = sum(abs(m.amount_residual_signed) for m in receivables)
            dashboard.total_payable = sum(abs(m.amount_residual_signed) for m in payables)
            dashboard.overdue_receivable = sum(
                abs(m.amount_residual_signed)
                for m in receivables.filtered(lambda r: r.invoice_date_due and r.invoice_date_due < today)
            )
            dashboard.overdue_payable = sum(
                abs(m.amount_residual_signed)
                for m in payables.filtered(lambda r: r.invoice_date_due and r.invoice_date_due < today)
            )
            dashboard.draft_invoices = self.env["account.move"].search_count(move_domain + [("state", "=", "draft")])
            dashboard.unpaid_customer_invoices = len(receivables)
            dashboard.unpaid_vendor_bills = len(payables)
            dashboard.matched_bank_lines = self.env["enhanced.bank.reconciliation.line"].search_count(
                [("company_id", "=", dashboard.company_id.id), ("state", "=", "matched")]
            )
            dashboard.unmatched_bank_lines = self.env["enhanced.bank.reconciliation.line"].search_count(
                [("company_id", "=", dashboard.company_id.id), ("state", "in", ("draft", "exception"))]
            )

    def action_refresh(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Gelismis Finans Panosu",
            "res_model": "enhanced.finance.dashboard",
            "view_mode": "form",
            "target": "current",
            "res_id": self.id,
        }
