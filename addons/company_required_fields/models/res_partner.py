from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains(
        'company_type', 'street', 'city', 'state_id', 'zip', 'country_id',
        'vat', 'phone', 'mobile', 'user_id', 'l10n_sa_additional_identification_scheme',
    )
    def _check_company_required_fields(self):
        for partner in self:
            if partner.company_type != 'company':
                continue

            required_fields = {
                'street': _('Street'),
                'city': _('City'),
                'state_id': _('State'),
                'zip': _('Zip'),
                'country_id': _('Country'),
                'vat': _('VAT / Tax ID'),
                'phone': _('Phone'),
                'mobile': _('Mobile'),
                'l10n_sa_additional_identification_scheme': _('Additional Identification Scheme'),
                'user_id': _('SalePerson'),
            }

            missing = [
                label for fname, label in required_fields.items()
                if not partner[fname]
            ]

            if missing:
                raise ValidationError(
                    _('For a Company contact, the following fields are required:\n- %s')
                    % '\n- '.join(missing)
                )