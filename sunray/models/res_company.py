from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = "res.company"
    
    company_lead_approval = fields.Boolean(string='Lead Approval', company_dependent=True)