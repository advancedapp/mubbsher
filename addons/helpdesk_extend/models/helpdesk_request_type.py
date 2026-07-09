from odoo import fields, models


class HelpdeskRequestType(models.Model):
    _name = 'helpdesk.request.type'
    _description = 'Helpdesk Request Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)