# helpdesk_portal/__manifest__.py
{
    'name': 'Helpdesk Portal',
    'version': '18.0.1.0.0',
    'summary': 'Portal ticket form, reopen workflow, and Mubbsher branding',
    'category': 'Helpdesk',
    'author': 'Mubbsher',
    'license': 'LGPL-3',
    'depends': ['helpdesk_mgmt'],
    'data': [
        'views/portal_templates.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'helpdesk_portal/static/src/scss/branding.scss',
            'helpdesk_portal/static/src/fonts/LamaSans-Medium.ttf',
            'helpdesk_portal/static/src/fonts/LamaSans-Black.ttf',
        ],
    },
    'installable': True,
}