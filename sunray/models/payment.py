from odoo import models, fields, api, _


class paypreliminary(models.Model):
    _name = 'payment.request'
    _description = 'Payment Request'
    
    pr_no = fields.Char(string='PR_ No.')
    issue_date = fields.Date(string='Date of Issue')
    request_company = fields.Char(string='Requesting Company')
    item_type = fields.Selection ([
              ('fixed asset','Fixed Asset'),
              ('inventory','Inventory'),
              ('maintenance','Maintenance'),
              ('supplies','Supplies'),
              ('others','Others')],
              string ='Item type',
              required=True)
    name = fields.Char(string='Name')
    line_ids = fields.One2many('purchase.request.line','purchase_id',string='Purchases')
    description = fields.Char(string='Description')
    company_name = fields.Char(string='Company Name')
    contact_person = fields.Char(string='Contact Person')
    contact_email = fields.Char(string='Email Address')
    contact_phone = fields.Char(string='Phone')


class purchaserequesttable(models.Model):
    _name = 'purchase.request.line'
    _description = 'Purchase Request Line'

    purchase_id = fields.Many2one(comodel_name='payment.request')
    material = fields.Char(string='Material Need')
    specification = fields.Char(string='Specification')
    part_no = fields.Char(string='Part No')
    quantity = fields.Char(string='Quantity')
    unit = fields.Char(string='Unit')
