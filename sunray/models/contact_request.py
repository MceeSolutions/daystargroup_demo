from odoo import models, fields


class ContactRequest(models.Model):
    _name = "new.contact.request"
    _description = 'Contact Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Name')
    email = fields.Char(string='Email')
