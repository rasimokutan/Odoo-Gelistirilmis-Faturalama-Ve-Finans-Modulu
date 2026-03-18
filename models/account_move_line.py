from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    finance_primary_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Birincil Analitik Hesap",
        compute="_compute_finance_analytic_helpers",
    )
    finance_primary_analytic_name = fields.Char(
        string="Analitik Ozet",
        compute="_compute_finance_analytic_helpers",
    )

    @api.depends("analytic_distribution")
    def _compute_finance_analytic_helpers(self):
        for line in self:
            analytic_account = False
            label = False
            if line.analytic_distribution:
                first_account_id = next(iter(line.analytic_distribution.keys()))
                analytic_account = self.env["account.analytic.account"].browse(int(first_account_id))
                label = ", ".join(
                    "%s (%s%%)" % (account.display_name, percentage)
                    for account, percentage in (
                        (
                            self.env["account.analytic.account"].browse(int(account_id)),
                            value,
                        )
                        for account_id, value in line.analytic_distribution.items()
                    )
                )
            line.finance_primary_analytic_account_id = analytic_account
            line.finance_primary_analytic_name = label
