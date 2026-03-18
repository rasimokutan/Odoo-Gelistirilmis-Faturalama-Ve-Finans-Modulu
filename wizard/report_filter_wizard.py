from odoo import _, fields, models


class EnhancedFinanceReportFilterWizard(models.TransientModel):
    _name = "enhanced.finance.report.filter.wizard"
    _description = "Gelismis Finans Rapor Filtre Sihirbazi"

    report_type = fields.Selection(
        [
            ("partner_aging", "Cari Yaslandirma Raporu"),
            ("overdue_invoice", "Gecikmis Fatura Raporu"),
            ("budget_performance", "Butce Performans Raporu"),
            ("bank_status", "Banka Mutabakat Durum Raporu"),
            ("analytic_summary", "Analitik Ozet Raporu"),
        ],
        string="Rapor",
        required=True,
        default="partner_aging",
    )
    company_id = fields.Many2one("res.company", string="Sirket", default=lambda self: self.env.company)
    date_from = fields.Date(string="Baslangic Tarihi")
    date_to = fields.Date(string="Bitis Tarihi")
    partner_id = fields.Many2one("res.partner", string="Cari")
    journal_id = fields.Many2one("account.journal", string="Gunluk")
    currency_id = fields.Many2one("res.currency", string="Para Birimi")
    overdue_only = fields.Boolean(string="Sadece Gecikmisler")
    posted_only = fields.Boolean(string="Sadece Onayli Kayitlar", default=True)

    def action_open_report(self):
        self.ensure_one()
        action_map = {
            "partner_aging": "enhanced_invoicing_accounting.action_partner_aging_report",
            "overdue_invoice": "enhanced_invoicing_accounting.action_overdue_invoice_report",
            "budget_performance": "enhanced_invoicing_accounting.action_budget_performance_report",
            "bank_status": "enhanced_invoicing_accounting.action_bank_status_report",
            "analytic_summary": "enhanced_invoicing_accounting.action_analytic_summary_report",
        }
        action = self.env.ref(action_map[self.report_type]).read()[0]
        domain = []
        if self.company_id:
            domain.append(("company_id", "=", self.company_id.id))
        if self.partner_id and "partner_id" in self.env[action["res_model"]]._fields:
            domain.append(("partner_id", "=", self.partner_id.id))
        if self.journal_id and "journal_id" in self.env[action["res_model"]]._fields:
            domain.append(("journal_id", "=", self.journal_id.id))
        if self.currency_id and "currency_id" in self.env[action["res_model"]]._fields:
            domain.append(("currency_id", "=", self.currency_id.id))
        if self.date_from:
            for field_name in ("date", "invoice_date", "date_from"):
                if field_name in self.env[action["res_model"]]._fields:
                    domain.append((field_name, ">=", self.date_from))
                    break
        if self.date_to:
            for field_name in ("date", "invoice_date", "date_to"):
                if field_name in self.env[action["res_model"]]._fields:
                    domain.append((field_name, "<=", self.date_to))
                    break
        if self.overdue_only:
            report_fields = self.env[action["res_model"]]._fields
            if "overdue_amount" in report_fields:
                domain.append(("overdue_amount", ">", 0))
            elif "overdue_days" in report_fields:
                domain.append(("overdue_days", ">", 0))
            elif "exception_flag" in report_fields:
                domain.append(("exception_flag", "=", True))
        if self.posted_only and "state" in self.env[action["res_model"]]._fields:
            domain.append(("state", "=", "posted"))
        action["domain"] = domain
        return action
