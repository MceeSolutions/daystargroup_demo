from odoo import models, fields, api


class SiteCodeRequest(models.Model):
    _name = "site.code.request"
    _description = 'Site Code Request'
    
    @api.multi
    def name_get(self):
        res = []
        for site in self:
            result = site.name
            if not site.name:
                result = str(site.state_id.name) + " " + "-" + " " + str(site.partner_id.name) + " - " + str(site.area)
            res.append((site.id, result))
        return res
    
    @api.multi
    def _default_partner_id(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        return leads.partner_id
    
    name = fields.Char('name')
    state_id = fields.Many2one(comodel_name='res.country.state', string='Site location (State)', required=True, track_visibility='onchange')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', required=True, default=_default_partner_id)
    area = fields.Char(string="Site Area", required=True)
    active = fields.Boolean('Active', default=False)
    
    @api.multi
    def action_request_information_apply(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        leads.write({'site_code_request_id': self.id})
        leads.button_request_site_code()
    
class SiteCodeRequested(models.TransientModel):
    _name = 'site.code.requested'
    _description = 'Get Request Information'

    site_code_request_id = fields.Many2one('site.code.request', 'site code request')

    @api.multi
    def action_request_information_apply(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        leads.write({'site_code_request_id': self.site_code_request_id.id})
        leads.button_request_site_code()