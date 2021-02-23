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


class SiteCode(models.Model):
    _name = "site.code"
    _description = "Site Code"
    _order = "name"
    _inherits = {'stock.location': 'location_id'}
    
    @api.multi
    def get_display_name(self):
        self.display_name = str(self.name) + " " + "-" + " " + str(self.partner_id.name) + " - " + str(self.site_area)
        
    @api.multi
    def name_get(self):
        res = []
        for site in self:
            result = site.name
            if site.name:
                result = str(site.name) + " " + "-" + " " + str(site.partner_id.name) + " - " + str(site.site_area)
            res.append((site.id, result))
        return res
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.partner_id = self.project_id.partner_id
        self.state_id = self.project_id.site_location_id
        self.site_area = self.project_id.site_area
        return {}
        
    location_id = fields.Many2one('stock.location', string='Location', ondelete="restrict", required=True)
    state_id = fields.Many2one(comodel_name='res.country.state', string='Site location (State)', required=True, track_visibility='onchange')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', required=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', required=False)
    active = fields.Boolean('Active', default='True')
    site_area = fields.Char('Site Area')
    stored_display_name = fields.Char(string="stored_display_name")
    display_name = fields.Char(string="display_name", store=True)
    num = fields.Integer(string="Num", store=True)
    site_address = fields.Char(string='Site Address')
    address_number = fields.Char(string='Number')
    address_street = fields.Char(string='Street')
    address_city = fields.Char(string='City')
    address_state_id = fields.Many2one(comodel_name="res.country.state", string='State', ondelete='restrict', related='state_id')
    address_country_id = fields.Many2one(comodel_name='res.country', string='Country', ondelete='restrict', related='state_id.country_id')
    lead_id = fields.Many2one(comodel_name='crm.lead', string='Lead / Opportunity')
    
    @api.multi
    def _check_site_code(self, vals):
        site = self.env['site.code'].search([('name','=',vals['name'])])
        if site:
            raise UserError(_('Site Code Must Unique!'))
    
    @api.model
    def create(self, vals):
        self._check_site_code(vals)
        site = self.env['res.country.state'].search([('id','=',vals['state_id'])])
        client = self.env['res.partner'].search([('id','=',vals['partner_id'])])
        if client.parent_account_number:
            code = client.parent_account_number + "_" + site.code
        else:
            raise UserError(_('There is no customer code for the customer'))
        
        no = self.env['ir.sequence'].next_by_code('project.site.code')
        site_code = code + "_" +  str(no)
        vals['usage'] = 'customer'
        return super(SiteCode, self).create(vals)
    
    @api.multi
    def create_project_from_site_code(self):
        if self.lead_id:
            if not self.lead_id.site_code_id:
                self.lead_id.site_code_id = self.id
                self.lead_id.create_project_from_lead()
                self.project_id = self.lead_id.project_id
            else:
                self.lead_id.create_project_from_lead()
                self.project_id = self.lead_id.project_id
        else:
            project_line = self.env['project.project'].create({
                 'site_code_id': self.id,
                 'crm_lead_id': self.lead_id.id,
                 'name': self.name,
                 'partner_id': self.partner_id.id,
                 'site_area': self.site_area,
                 'site_address': self.site_address,
                 'site_location_id': self.state_id.id
            })
            self.project_id = project_line
        return {}
    
    @api.onchange('lead_id')
    def _onchange_lead_id(self):
        self.partner_id = self.lead_id.partner_id
        
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.name = str(self.partner_id.parent_account_number) + '_'
        
    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.partner_id:
            self.name = str(self.partner_id.parent_account_number) + '_' + str(self.state_id.code) + '_'
