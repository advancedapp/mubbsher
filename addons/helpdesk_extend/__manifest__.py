{
    'name': 'Helpdesk Extend',
    'version': '18.0.1.0.0',
    'summary': 'Custom ticket fields, stages, and workflow logic for Mubbsher helpdesk',
    'category': 'Helpdesk',
    'author': 'Mubbsher',
    'license': 'LGPL-3',
    'depends': ['helpdesk_mgmt', 'helpdesk_mgmt_sla', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/helpdesk_data.xml',
        'data/mail_template_data.xml',
        'views/helpdesk_service_type_views.xml',
        'views/helpdesk_request_type_views.xml',
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
}