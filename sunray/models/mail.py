from odoo import models, fields


class Message(models.Model):
    _inherit = 'mail.message'
    
    add_sign = fields.Boolean(default=False)
