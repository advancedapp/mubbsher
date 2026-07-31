# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleSubscriptionStage(models.Model):
    _name = "sale.subscription.stage"
    _description = "مرحلة الاشتراك"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True, string="الاسم")
    sequence = fields.Integer(string="التسلسل")
    in_progress = fields.Boolean(string="قيد التنفيذ", default=False)
    fold = fields.Boolean(string="مطوي في كانبان")
    description = fields.Text(translate=True, string="الوصف")
    type = fields.Selection(
        [
            ("draft", "مسودة"),
            ("pre", "جاهز للبدء"),
            ("in_progress", "قيد التنفيذ"),
            ("post", "مغلق"),
        ],
        default="pre",
        string="النوع",
    )

    @api.constrains("type")
    def _check_lot_product(self):
        post_stages = self.env["sale.subscription.stage"].search(
            [("type", "=", "post")]
        )
        if len(post_stages) > 1:
            raise ValidationError(
                self.env._("يوجد بالفعل مرحلة من نوع 'مغلق' محددة")
            )