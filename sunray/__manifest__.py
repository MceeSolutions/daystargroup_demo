# -*- coding: utf-8 -*-
{
    'name': "Sunray",
    'summary': """
        Sunray Modules""",
    'description': """
        Long description of module's purpose
    """,
    'author': "MCEE Solutions",
    'website': "http://www.mceesolutions.com",
    'category': 'Sunray',
    'version': '0.132',
    'depends': [
        'base',
        'hr',
        'hr_payroll',
        'repair',
        'website_form_editor', 
        'crm',
        'sale',
        'hr_expense',
        'hr_holidays',
        'project',
        'purchase',
        'helpdesk',
        'stock',
        'product',
        'account_budget',
        'purchase_requisition',
        'mrp',
        'mrp_maintenance',
        'sale_subscription',
        'stock_barcode',
    ],
    'data': [
        'security/sunray_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        # 'views/stock_views.xml',
        # 'views/vendor_request_info_template.xml',
        # 'views/purchase_view.xml',
        'views/'

    ],
    'qweb': [
        'views/chatter.xml'
    ],
}
