# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleSubscriptionTag(models.Model):
    _name = "sale.subscription.tag"
    _description = "علامات اشتراك المبيعات"

    name = fields.Char("اسم العلامة", required=True, translate=True)