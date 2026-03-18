from odoo import fields, models, tools


class EnhancedFinancePartnerAgingReport(models.Model):
    _name = "enhanced.finance.partner.aging.report"
    _description = "Partner Aging Report"
    _auto = False
    _rec_name = "partner_id"

    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    total_amount = fields.Monetary(string="Total", currency_field="currency_id", readonly=True)
    overdue_amount = fields.Monetary(string="Overdue", currency_field="currency_id", readonly=True)
    bucket_0_30 = fields.Monetary(string="0-30", currency_field="currency_id", readonly=True)
    bucket_31_60 = fields.Monetary(string="31-60", currency_field="currency_id", readonly=True)
    bucket_61_90 = fields.Monetary(string="61-90", currency_field="currency_id", readonly=True)
    bucket_90_plus = fields.Monetary(string="90+", currency_field="currency_id", readonly=True)
    overdue_invoice_count = fields.Integer(string="Overdue Invoice Count", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    move.partner_id AS partner_id,
                    move.company_id AS company_id,
                    move.currency_id AS currency_id,
                    SUM(ABS(move.amount_residual_signed)) AS total_amount,
                    SUM(CASE WHEN move.invoice_date_due < CURRENT_DATE THEN ABS(move.amount_residual_signed) ELSE 0 END) AS overdue_amount,
                    SUM(CASE WHEN move.invoice_date_due < CURRENT_DATE AND CURRENT_DATE - move.invoice_date_due <= 30 THEN ABS(move.amount_residual_signed) ELSE 0 END) AS bucket_0_30,
                    SUM(CASE WHEN move.invoice_date_due < CURRENT_DATE AND CURRENT_DATE - move.invoice_date_due BETWEEN 31 AND 60 THEN ABS(move.amount_residual_signed) ELSE 0 END) AS bucket_31_60,
                    SUM(CASE WHEN move.invoice_date_due < CURRENT_DATE AND CURRENT_DATE - move.invoice_date_due BETWEEN 61 AND 90 THEN ABS(move.amount_residual_signed) ELSE 0 END) AS bucket_61_90,
                    SUM(CASE WHEN move.invoice_date_due < CURRENT_DATE AND CURRENT_DATE - move.invoice_date_due > 90 THEN ABS(move.amount_residual_signed) ELSE 0 END) AS bucket_90_plus,
                    COUNT(*) FILTER (WHERE move.invoice_date_due < CURRENT_DATE) AS overdue_invoice_count
                FROM account_move move
                WHERE move.state = 'posted'
                    AND move.move_type IN ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt')
                    AND move.payment_state IN ('not_paid', 'partial', 'in_payment')
                    AND move.partner_id IS NOT NULL
                GROUP BY move.partner_id, move.company_id, move.currency_id
            )
            """
        )


class EnhancedFinanceOverdueInvoiceReport(models.Model):
    _name = "enhanced.finance.overdue.invoice.report"
    _description = "Overdue Invoice Report"
    _auto = False
    _rec_name = "move_name"

    move_id = fields.Many2one("account.move", string="Invoice", readonly=True)
    move_name = fields.Char(string="Invoice Number", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    journal_id = fields.Many2one("account.journal", string="Journal", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    invoice_date = fields.Date(string="Invoice Date", readonly=True)
    due_date = fields.Date(string="Due Date", readonly=True)
    overdue_days = fields.Integer(string="Overdue Days", readonly=True)
    residual_amount = fields.Monetary(string="Residual", currency_field="currency_id", readonly=True)
    payment_state = fields.Selection(selection=[("not_paid", "Not Paid"), ("partial", "Partial"), ("in_payment", "In Payment")], readonly=True)
    state = fields.Selection(selection=[("posted", "Posted")], readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    move.id AS id,
                    move.id AS move_id,
                    move.name AS move_name,
                    move.partner_id AS partner_id,
                    move.company_id AS company_id,
                    move.journal_id AS journal_id,
                    move.currency_id AS currency_id,
                    move.invoice_date AS invoice_date,
                    move.invoice_date_due AS due_date,
                    (CURRENT_DATE - move.invoice_date_due) AS overdue_days,
                    ABS(move.amount_residual_signed) AS residual_amount,
                    move.payment_state AS payment_state,
                    move.state AS state
                FROM account_move move
                WHERE move.state = 'posted'
                    AND move.move_type IN ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt')
                    AND move.payment_state IN ('not_paid', 'partial', 'in_payment')
                    AND move.invoice_date_due < CURRENT_DATE
            )
            """
        )


class EnhancedFinanceBudgetPerformanceReport(models.Model):
    _name = "enhanced.finance.budget.performance.report"
    _description = "Budget Performance Report"
    _auto = False
    _rec_name = "budget_id"

    budget_id = fields.Many2one("enhanced.finance.budget", string="Budget", readonly=True)
    budget_line_id = fields.Many2one("enhanced.finance.budget.line", string="Budget Line", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account", readonly=True)
    account_id = fields.Many2one("account.account", string="Account", readonly=True)
    planned_amount = fields.Float(string="Planned", readonly=True)
    practical_amount = fields.Float(string="Practical", readonly=True)
    achievement_rate = fields.Float(string="Achievement %", readonly=True)
    state = fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed"), ("closed", "Closed")], readonly=True)
    date_from = fields.Date(string="Date From", readonly=True)
    date_to = fields.Date(string="Date To", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    line.id AS id,
                    line.budget_id AS budget_id,
                    line.id AS budget_line_id,
                    line.company_id AS company_id,
                    line.analytic_account_id AS analytic_account_id,
                    line.account_id AS account_id,
                    line.planned_amount AS planned_amount,
                    ABS(COALESCE(SUM(aal.amount), 0)) AS practical_amount,
                    CASE
                        WHEN line.planned_amount = 0 THEN 0
                        ELSE (ABS(COALESCE(SUM(aal.amount), 0)) / line.planned_amount) * 100
                    END AS achievement_rate,
                    budget.state AS state,
                    budget.date_from AS date_from,
                    budget.date_to AS date_to
                FROM enhanced_finance_budget_line line
                JOIN enhanced_finance_budget budget ON budget.id = line.budget_id
                LEFT JOIN account_analytic_line aal
                    ON aal.company_id = line.company_id
                    AND aal.account_id = line.analytic_account_id
                    AND aal.general_account_id = line.account_id
                    AND aal.date >= budget.date_from
                    AND aal.date <= budget.date_to
                GROUP BY
                    line.id,
                    line.budget_id,
                    line.company_id,
                    line.analytic_account_id,
                    line.account_id,
                    line.planned_amount,
                    budget.state,
                    budget.date_from,
                    budget.date_to
            )
            """
        )


class EnhancedFinanceBankStatusReport(models.Model):
    _name = "enhanced.finance.bank.status.report"
    _description = "Bank Reconciliation Status Report"
    _auto = False
    _rec_name = "description"

    reconciliation_id = fields.Many2one("enhanced.bank.reconciliation", string="Reconciliation", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    journal_id = fields.Many2one("account.journal", string="Journal", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    description = fields.Char(string="Description", readonly=True)
    reference = fields.Char(string="Reference", readonly=True)
    amount = fields.Monetary(string="Amount", currency_field="currency_id", readonly=True)
    state = fields.Selection(
        [("draft", "Draft"), ("suggested", "Suggested"), ("matched", "Matched"), ("exception", "Exception")],
        readonly=True,
    )
    exception_flag = fields.Boolean(string="Exception", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    line.id AS id,
                    line.reconciliation_id AS reconciliation_id,
                    line.company_id AS company_id,
                    line.journal_id AS journal_id,
                    line.partner_id AS partner_id,
                    line.currency_id AS currency_id,
                    line.date AS date,
                    line.description AS description,
                    line.reference AS reference,
                    line.amount AS amount,
                    line.state AS state,
                    line.exception_flag AS exception_flag
                FROM enhanced_bank_reconciliation_line line
            )
            """
        )


class EnhancedFinanceAnalyticSummaryReport(models.Model):
    _name = "enhanced.finance.analytic.summary.report"
    _description = "Analytic Summary Report"
    _auto = False
    _rec_name = "analytic_account_id"

    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account", readonly=True)
    general_account_id = fields.Many2one("account.account", string="Account", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    journal_id = fields.Many2one("account.journal", string="Journal", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    amount = fields.Float(string="Amount", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    aal.id AS id,
                    aal.company_id AS company_id,
                    aal.date AS date,
                    aal.account_id AS analytic_account_id,
                    aal.general_account_id AS general_account_id,
                    aml.partner_id AS partner_id,
                    aml.product_id AS product_id,
                    move.journal_id AS journal_id,
                    company.currency_id AS currency_id,
                    aal.amount AS amount
                FROM account_analytic_line aal
                LEFT JOIN account_move_line aml ON aml.id = aal.move_line_id
                LEFT JOIN account_move move ON move.id = aml.move_id
                LEFT JOIN res_company company ON company.id = aal.company_id
            )
            """
        )
