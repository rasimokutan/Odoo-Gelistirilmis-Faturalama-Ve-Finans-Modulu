from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EnhancedBankImportWizard(models.TransientModel):
    _name = "enhanced.bank.import.wizard"
    _description = "Gelismis Banka Ice Aktarma Sihirbazi"
    _inherit = "enhanced.bank.import.mixin"

    reconciliation_id = fields.Many2one(
        "enhanced.bank.reconciliation",
        string="Mutabakat",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Banka Gunlugu",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Sirket",
        required=True,
        default=lambda self: self.env.company,
    )
    file_data = fields.Binary(string="CSV Dosyasi", required=True)
    file_name = fields.Char(string="Dosya Adi")

    def action_import(self):
        self.ensure_one()
        rows = self._parse_bank_csv(self.file_data)
        reconciliation = self.reconciliation_id
        if not reconciliation:
            reconciliation = self.env["enhanced.bank.reconciliation"].create(
                {
                    "journal_id": self.journal_id.id,
                    "company_id": self.company_id.id,
                    "currency_id": self.company_id.currency_id.id,
                }
            )
        Partner = self.env["res.partner"]
        Currency = self.env["res.currency"]
        for row in rows:
            currency = Currency.search([("name", "=", row["currency"])], limit=1) or self.company_id.currency_id
            partner = False
            if row.get("partner"):
                partner = Partner.search(
                    ["|", ("name", "=", row["partner"]), ("ref", "=", row["partner"])],
                    limit=1,
                )
            self.env["enhanced.bank.reconciliation.line"].create(
                {
                    "reconciliation_id": reconciliation.id,
                    "date": row["date"],
                    "description": row["description"],
                    "reference": row["reference"],
                    "amount": float(row["amount"]),
                    "currency_id": currency.id,
                    "partner_id": partner.id if partner else False,
                }
            )
        reconciliation.action_run_auto_match()
        return {
            "type": "ir.actions.act_window",
            "name": _("Banka Mutabakati"),
            "res_model": "enhanced.bank.reconciliation",
            "view_mode": "form",
            "res_id": reconciliation.id,
            "target": "current",
        }
