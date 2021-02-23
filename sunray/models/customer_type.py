from odoo import models, fields, api, _


class CustomerType(models.Model):
    _name = "customer.type"
    _description = 'Customer Type'
    
    name = fields.Char(string='Name', required=True)