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

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sunray',
<<<<<<< HEAD
    'version': '0.41',

=======
    'version': '0.40',
>>>>>>> 38bc9ac8ae7c442b24cf8ad69512e2f68d782cb5
    # any module necessary for this one to work correctly
    'depends': ['base','hr','crm','sale','hr_expense','hr_holidays','project','purchase','helpdesk','stock','product','account_budget','purchase_requisition','mrp'],

    # always loaded
    'data': [
        'security/sunray_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/views.xml',
        'views/stock_views.xml',
        'views/vendor_request_info_template.xml',
        #'views/templates.xml',
        #'views/website_netcom_hr_recruitment_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
}
