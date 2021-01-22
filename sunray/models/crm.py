from odoo import models, fields, api

class Lead(models.Model):
    _name = "crm.lead"
    _inherit = 'crm.lead'
    
    type_of_offer = fields.Selection([('saas', 'SaaS'), ('pass', 'PaaS'),('battery', 'Battery'),
                                      ('pass_diesel', 'PaaS Diesel'),('lease', 'Lease to'), ('own', 'Own'),
                                      ('sale', 'Sale')], string='Type of Offer', required=False,default='saas')
    size = fields.Float(string='Size (kWp)')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    
    budget = fields.Float(string='Estimate project costs')
    legal_review = fields.Boolean(string='Legal Review')
    legal_review_done = fields.Boolean(string='Legal Review Done')
    
    site_location_id = fields.Many2one(comodel_name='res.country.state', string='Site Location', domain=[('country_id.name','=','Nigeria')])

    client_type = fields.Many2one(comodel_name='customer.type', related='partner_id.customer_type_id', string='Customer Type')
    site_area = fields.Char(string='Site Area', related='site_code_id.site_area')
    site_address = fields.Char(string='Site Address')
    site_type = fields.Char(string='Site Type')

    region = fields.Char(string='Region', related='site_location_id.region')
    country_id = fields.Many2one(comodel_name='res.country', string="Country")

    contract_duration = fields.Float(string='Contract Duration (year)')
    coordinates = fields.Char(string='Coordinates')
    
    type_of_offer = fields.Selection([('lease_to_own', 'Lease to own'), ('pass_battery', 'PaaS Battery'), 
                                      ('pass_diesel', 'PaaS Diesel'), ('solar', 'Solar Only'),('saas', 'SaaS'), ('sale', 'Sale')], string='Service Type', required=False,default='saas')

    
    tariff_per_kwp = fields.Float(string='Tariff per kWh')
    monthly_service_fees = fields.Float(string='Monthly Service fees')
    sales_price = fields.Float(string="Sale Revenue")
    
    lead_approval = fields.Boolean(string="lead approval", related='company_id.company_lead_approval')
    site_location_id = fields.Many2one(comodel_name='res.country.state', string='Site Location', related='site_code_id.state_id', domain=[('country_id.name','=','Nigeria')])
    
    request_site_code = fields.Boolean(string="Request Site Code", copy=False)
    
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    total_capacity = fields.Float(string='Total Capacity (kWp)')
    solar_capacity = fields.Float(string='Solar Capacity (kWp)')
    
    opportunity_created_date = fields.Datetime(string="Opportunity Creation Date")
    nord_type_of_sales = fields.Selection([('tendering', 'Tendering'), ('regular', 'Regular')], string='Type of Sales')
    nord_type_of_offer = fields.Selection([('asset_mang', 'Asset Management'), ('sales_of_drill', 'Sales of drilling fluids and chemicals'), ('sales_of_tools', 'Sales of tools and equipment')], string='Type of Offer')
    nord_size = fields.Char(string='Size.')
    
    private_lead = fields.Boolean(string="private lead")
    site_code_request_id = fields.Many2one('site.code.request', string='Request Site Code', index=True, track_visibility='onchange')
    
    project_id = fields.Many2one(comodel_name='project.project', string='Project', required=False)
            
    @api.multi
    def create_project_from_lead(self):
        project_line = self.env['project.project'].create({
            'crm_lead_id': self.id,
            'name': self.site_code_id.name,
            'partner_id': self.partner_id.id,
            'site_code_id': self.site_code_id.id,
            'site_area': self.site_area,
            'site_address': self.site_address,
            'site_type': self.site_type,
            'country_id': self.country_id.id,
            'lease_duration': self.contract_duration,
            'coordinates': self.coordinates,
            'type_of_offer': self.type_of_offer,
            'tariff_per_kwp': self.tariff_per_kwp,
            'site_location_id': self.site_location_id.id,
            'total_capacity': self.total_capacity,
            'solar_capacity': self.solar_capacity,
            'sales_price': self.sales_price
            })
        self.project_id = project_line
        return {}
    
    @api.multi
    def action_set_won_rainbowman(self):
        self.ensure_one()
        self.action_set_won()
        self.create_project_from_lead()
    
    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return {}
    
    @api.multi
    def button_request_site_code(self):
        self.request_site_code = True
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_site_code_creation')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "A site code is needed for this '{}' oppurtunity for customer '{}', Site Location '{}' and Site Area '{}' ".format(self.name, self.site_code_request_id.partner_id.name, self.site_code_request_id.state_id.name, self.site_code_request_id.area)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
        return {}
    
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_hr_line_manager')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Created Lead {} is ready for Approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
        return {}
    
    @api.multi
    def button_approve(self):
        self.write({'state': 'approve'})
        self.active = True
        self.send_introductory_mail()
        subject = "Created Lead {} has been approved".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_reject(self):
        self.write({'state': 'reject'})
        return {}
    
    @api.model
    def create(self, vals):
        result = super(Lead, self).create(vals)
        result.send_introductory_mail()
        result.opportunity_created_date = result.create_date
        return result
    
    @api.multi
    def check_lead_approval(self):
        if self.company_id.company_lead_approval == True:
            self.active = False
        else:
            self.send_introductory_mail()
    
    @api.multi
    def button_submit_legal(self):
        self.legal_review = True
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_legal_team')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Opportunity '{}' needs a review from the legal team".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
    
    @api.multi
    def button_submit_legal_done(self):
        self.legal_review_done = True
        subject = "Opportunity {} has been reviewed by the legal team".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def send_introductory_mail(self):
        config = self.env['mail.template'].sudo().search([('name','=','Introductory Email Template')], limit=1)
        mail_obj = self.env['mail.mail']
        if config:
            values = config.generate_email(self.id)
            mail = mail_obj.create(values)
            if mail:
                mail.send()
                subject = "Introductory message for {} has been sent to client".format(self.name)
                partner_ids = []
                for partner in self.sheet_id.message_partner_ids:
                    partner_ids.append(partner.id)
                self.sheet_id.message_post(subject=subject,body=subject,partner_ids=partner_ids)

    @api.multi
    def send_site_audit_request_mail(self):
        config = self.env['mail.template'].sudo().search([('name','=','Site Audit Request Template')], limit=1)
        mail_obj = self.env['mail.mail']
        if config:
            values = config.generate_email(self.id)
            mail = mail_obj.create(values)
            if mail:
                mail.send()
                subject = "Site audit request {} has been sent to client".format(self.name)
                partner_ids = []
                for partner in self.message_partner_ids:
                    partner_ids.append(partner.id)
                self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def create_project(self):
        """
        Method to open create project form
        """
        partner_id = self.partner_id
        site_location_id = self.site_location_id
        default_site_code = self.default_site_code
        view_ref = self.env['ir.model.data'].get_object_reference('project', 'edit_project')
        view_id = view_ref[1] if view_ref else False
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Project'),
            'res_model': 'project.project',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_partner_id': partner_id.id, 'default_name': self.name, 'default_site_location_id': self.site_location_id.id, 'default_default_site_code': self.default_site_code,  'default_crm_lead_id': self.id}
        }
        return res
    
    @api.multi
    def create_manufacturing_order(self):
        """
        Method to open create purchase agreement form
        """

        partner_id = self.partner_id
        view_ref = self.env['ir.model.data'].get_object_reference('mrp', 'mrp_production_form_view')
        view_id = view_ref[1] if view_ref else False
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Manufacturing Order'),
            'res_model': 'mrp.production',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_origin': self.name}
        }
        return res


class Stage(models.Model):
    _name = "crm.stage"
    _inherit = "crm.stage"
    
    company_id = fields.Many2one('res.company', string='Company', store=True,
        default=lambda self: self.env.user.company_id, track_visibility='onchange')
    active = fields.Boolean(string='Active')