from odoo import _, api, fields, models


class EnhancedFinanceFollowupLog(models.Model):
    _name = "enhanced.finance.followup.log"
    _description = "Gelismis Finans Takip Kaydi"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sent_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Referans",
        required=True,
        copy=False,
        default=lambda self: _("Yeni"),
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cari",
        required=True,
        check_company=True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="Fatura",
        required=True,
        domain="[('move_type', 'in', ('out_invoice', 'out_receipt'))]",
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Sirket",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="invoice_id.currency_id",
        store=True,
        readonly=True,
    )
    due_date = fields.Date(string="Vade Tarihi", required=True)
    overdue_days = fields.Integer(string="Gecikme Gunu", required=True)
    reminder_level = fields.Selection(
        [("level_1", "1. Hatirlatma"), ("level_2", "2. Hatirlatma"), ("final", "Son Uyari")],
        string="Hatirlatma Seviyesi",
        required=True,
        default="level_1",
        tracking=True,
    )
    sent_date = fields.Datetime(
        string="Gonderim Tarihi",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [("draft", "Taslak"), ("sent", "Gonderildi"), ("cancelled", "Iptal")],
        string="Durum",
        default="draft",
        tracking=True,
        required=True,
    )
    notes = fields.Text(string="Notlar")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Yeni")) == _("Yeni"):
                vals["name"] = sequence.next_by_code("enhanced.finance.followup") or _("Yeni")
        records = super().create(vals_list)
        return records

    def action_mark_sent(self):
        self.write({"state": "sent", "sent_date": fields.Datetime.now()})
        for record in self:
            record.invoice_id.message_post(
                body=_("Finans follow-up olusturuldu: %s") % dict(self._fields["reminder_level"].selection).get(record.reminder_level)
            )
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    @api.model
    def cron_generate_overdue_followups(self):
        today = fields.Date.context_today(self)
        overdue_invoices = self.env["account.move"].search(
            [
                ("company_id", "in", self.env.companies.ids),
                ("state", "=", "posted"),
                ("move_type", "in", ("out_invoice", "out_receipt")),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
                ("invoice_date_due", "!=", False),
                ("invoice_date_due", "<", today),
            ]
        )
        for invoice in overdue_invoices:
            overdue_days = (today - invoice.invoice_date_due).days
            if overdue_days <= 15:
                level = "level_1"
            elif overdue_days <= 30:
                level = "level_2"
            else:
                level = "final"
            existing = self.search_count(
                [
                    ("invoice_id", "=", invoice.id),
                    ("reminder_level", "=", level),
                    ("state", "!=", "cancelled"),
                    ("sent_date", ">=", fields.Datetime.to_datetime(today)),
                ]
            )
            if existing:
                continue
            followup = self.create(
                {
                    "partner_id": invoice.partner_id.commercial_partner_id.id,
                    "invoice_id": invoice.id,
                    "company_id": invoice.company_id.id,
                    "due_date": invoice.invoice_date_due,
                    "overdue_days": overdue_days,
                    "reminder_level": level,
                    "notes": _("Cron tarafindan otomatik olusturuldu."),
                }
            )
            followup.action_mark_sent()
