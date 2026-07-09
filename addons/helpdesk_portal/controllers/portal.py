from odoo import http
from odoo.http import request


class HelpdeskPortal(http.Controller):

    @http.route('/helpdesk/ticket/reopen/<int:ticket_id>', type='http',
                auth='user', website=True, methods=['POST'])
    def portal_reopen_ticket(self, ticket_id, reason='', **kwargs):
        ticket = request.env['helpdesk.ticket'].browse(ticket_id)
        if ticket.exists() and ticket.partner_id.id == request.env.user.partner_id.id:
            ticket.action_reopen_from_portal(reason)
        return request.redirect('/my/ticket/%s' % ticket_id)