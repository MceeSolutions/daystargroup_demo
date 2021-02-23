from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    lead_approval = fields.Boolean(string='Lead Approval', company_dependent=False, readonly=False, related='company_id.company_lead_approval')