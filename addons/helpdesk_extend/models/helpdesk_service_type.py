from odoo import fields, models


class HelpdeskServiceType(models.Model):
    _name = 'helpdesk.service.type'
    _description = 'Helpdesk Service Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)