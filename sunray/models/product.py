from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    business_unit = fields.Char(string='Business Unit')
    manufacturer = fields.Char(string='Manufacturer')
    dimension = fields.Char(string='Dimension (mm) (W x D x H)')
    manufacturer_part_number = fields.Char(string='Manufacturer part number')    
    brand = fields.Many2one('brand.type', string='Manufacturer', track_visibility='onchange', index=True)
    item_type = fields.Many2one('item.type', string='Item Type', track_visibility='onchange', index=True)