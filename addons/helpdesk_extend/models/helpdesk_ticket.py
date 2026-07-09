from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    service_type_id = fields.Many2one(
        'helpdesk.service.type',
        string='Service Type',
    )
    request_type = fields.Selection(
        [
            ('inquiry', 'Inquiry'),
            ('complaint', 'Complaint'),
            ('request', 'Request'),
        ],
        string='Request Type',
        default='inquiry',
        required=True,
    )
    request_subtype_id = fields.Many2one(
        'helpdesk.request.type',
        string='Request',
    )
    reopen_reason = fields.Text(string='Reopen Reason')

    @api.onchange('request_type')
    def _onchange_request_type(self):
        if self.request_type != 'request':
            self.request_subtype_id = False

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for ticket in tickets:
            ticket._notify_helpdesk_manager_new_ticket()
        return tickets

    def _notify_helpdesk_manager_new_ticket(self):
        # NOTE: confirm the actual XML ID for the manager group in your
        # installed helpdesk_mgmt version — commonly
        # 'helpdesk_mgmt.group_helpdesk_manager'.
        manager_group = self.env.ref(
            'helpdesk_mgmt.group_helpdesk_manager', raise_if_not_found=False
        )
        if not manager_group:
            return
        for user in manager_group.users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=_('New ticket needs assignment'),
                note=_('Ticket "%s" was submitted and needs to be assigned to a team member.') % self.name,
            )

    def action_reopen_from_portal(self, reason):
        self.ensure_one()
        reopen_stage = self.env.ref(
            'helpdesk_extend.stage_reopened', raise_if_not_found=False
        )
        self.write({
            'reopen_reason': reason,
            'stage_id': reopen_stage.id if reopen_stage else self.stage_id.id,
        })
        self.message_post(
            body=_('Ticket reopened by customer. Reason: %s') % reason
        )
        self._notify_helpdesk_manager_new_ticket()

    def action_close_ticket(self):
        self.ensure_one()
        closed_stage = self.env.ref(
            'helpdesk_extend.stage_completed', raise_if_not_found=False
        )
        if closed_stage:
            self.stage_id = closed_stage.id
        template = self.env.ref(
            'helpdesk_extend.mail_template_ticket_closed',
            raise_if_not_found=False,
        )
        if template and self.partner_id:
            template.send_mail(self.id, force_send=True)