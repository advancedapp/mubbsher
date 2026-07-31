# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class SaleSubscriptionCloseReason(models.Model):
    _name = "sale.subscription.close.reason"
    _description = "نموذج سبب الإغلاق"

    name = fields.Char(required=True, translate=True, string="الاسم")