from odoo import _, fields, models
from odoo.exceptions import UserError


class EnhancedFinanceFollowupWizard(models.TransientModel):
    _name = "enhanced.finance.followup.wizard"
    _description = "Enhanced Finance Follow-up Wizard"

    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices",
        domain="[('partner_id', 'child_of', partner_id), ('move_type', 'in', ('out_invoice', 'out_receipt')), ('state', '=', 'posted')]",
    )
    reminder_level = fields.Selection(
        [("level_1", "1. Hatirlatma"), ("level_2", "2. Hatirlatma"), ("final", "Son Uyari")],
        string="Reminder Level",
        required=True,
        default="level_1",
    )
    notes = fields.Text(string="Notes")

    def action_send_followup(self):
        self.ensure_one()
        invoices = self.invoice_ids or self.env["account.move"].search(
            [
                ("partner_id", "child_of", self.partner_id.id),
                ("move_type", "in", ("out_invoice", "out_receipt")),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
            ]
        )
        if not invoices:
            raise UserError(_("Takip gonderilecek uygun acik fatura bulunamadi."))
        today = fields.Date.context_today(self)
        for invoice in invoices:
            if not invoice.invoice_date_due or invoice.invoice_date_due >= today:
                continue
            log = self.env["enhanced.finance.followup.log"].create(
                {
                    "partner_id": self.partner_id.commercial_partner_id.id,
                    "invoice_id": invoice.id,
                    "company_id": invoice.company_id.id,
                    "due_date": invoice.invoice_date_due,
                    "overdue_days": (today - invoice.invoice_date_due).days,
                    "reminder_level": self.reminder_level,
                    "notes": self.notes or _("Manuel wizard ile olusturuldu."),
                }
            )
            log.action_mark_sent()
        return {"type": "ir.actions.act_window_close"}
