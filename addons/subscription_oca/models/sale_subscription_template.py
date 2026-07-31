# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SaleSubscriptionTemplate(models.Model):
    _name = "sale.subscription.template"
    _description = "قوالب الاشتراك"

    name = fields.Char(required=True, translate=True, string="الاسم")
    description = fields.Text(string="الشروط والأحكام", translate=True)
    recurring_interval = fields.Integer(string="كرر كل", default=1)
    recurring_rule_type = fields.Selection(
        [
            ("days", "يوم (أيام)"),
            ("weeks", "أسبوع (أسابيع)"),
            ("months", "شهر (أشهر)"),
            ("years", "سنة (سنوات)"),
        ],
        string="التكرار",
        default="months",
    )
    recurring_rule_boundary = fields.Selection(
        [("unlimited", "إلى الأبد"), ("limited", "ثابت")],
        string="المدة",
        default="unlimited",
    )
    invoicing_mode = fields.Selection(
        default="draft",
        string="طريقة الفوترة",
        selection=[
            ("draft", "مسودة"),
            ("invoice", "فاتورة"),
            ("invoice_send", "فاتورة وإرسال"),
            ("sale_and_invoice", "أمر بيع وفاتورة"),
        ],
    )
    code = fields.Char(string="الكود")
    recurring_rule_count = fields.Integer(default=1, string="عدد القواعد")
    invoice_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="البريد الإلكتروني للفاتورة",
        domain="[('model', '=', 'account.move')]",
    )
    product_ids = fields.One2many(
        comodel_name="product.template",
        inverse_name="subscription_template_id",
        string="المنتجات",
    )
    product_ids_count = fields.Integer(
        compute="_compute_product_ids_count", string="المنتجات"
    )
    subscription_ids = fields.One2many(
        comodel_name="sale.subscription",
        inverse_name="template_id",
        string="الاشتراكات",
    )
    subscription_count = fields.Integer(
        compute="_compute_subscription_count", string="الاشتراكات"
    )

    def _compute_subscription_count(self):
        data = self.env["sale.subscription"].read_group(
            domain=[("template_id", "in", self.ids)],
            fields=["template_id"],
            groupby=["template_id"],
        )
        count_dict = {
            item["template_id"][0]: item["template_id_count"] for item in data
        }
        for record in self:
            record.subscription_count = count_dict.get(record.id, 0)

    def action_view_subscription_ids(self):
        return {
            "name": self.name,
            "view_mode": "list,form",
            "res_model": "sale.subscription",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.subscription_ids.ids)],
        }

    def _get_date(self, date_start):
        self.ensure_one()
        return relativedelta(months=+self.recurring_rule_count) + date_start

    @api.depends("product_ids")
    def _compute_product_ids_count(self):
        for record in self:
            record.product_ids_count = len(record.product_ids)

    def action_view_product_ids(self):
        return {
            "name": self.name,
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "product.template",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.product_ids.ids)],
        }