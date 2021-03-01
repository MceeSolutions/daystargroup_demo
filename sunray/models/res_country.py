from odoo import models, fields


class CountryState(models.Model):
    _inherit = 'res.country.state'
    
    region = fields.Char(string='Region')