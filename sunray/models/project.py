from dateutil.relativedelta import relativedelta
from ast import literal_eval
from datetime import date
from odoo import models, fields, api, _


class Project(models.Model):
    _name = "project.project"
    _inherit = ['project.project', 'mail.thread', 'mail.activity.mixin', 'rating.mixin']
    _description = "Project"
    
    def _default_analytic(self):
        return self.env['account.analytic.account'].search([('name','=','Sunray')])
    
    @api.multi
    def name_get(self):
        res = []
        for project in self:
            result = project.name
            if project.site_code_id.name:
                result = str(project.site_code_id.name) + " " + "-" + " " + str(project.partner_id.name) + " - " + str(project.site_area)
            res.append((project.id, result))
        return res
    
    #def _default_account(self):
    #    return self.product_id.property_account_expense_id
    
    state = fields.Selection([
        ('kick_off', 'Kick off'),
        ('project_plan', 'Project plan'),
        ('supply_chain_project_execution', 'Supply Chain Project Execution'),
        ('qc_sign_off', 'Qc sign off'),
        ('customer_sign_off', 'Customer Sign off'),
        ('close_out', 'Close out'),
        ('installed', 'Installed'),
        ('decommissioned', 'Decommissioned'),
        ], string='Stage', readonly=False, index=True, copy=False, default='kick_off', track_visibility='onchange')
    
    name = fields.Char("Name", index=True, required=True, track_visibility='onchange')
    
    checklist_count = fields.Integer(compute="_checklist_count",string="Checklist", store=False)
    
    action_count = fields.Integer(compute="_action_count",string="Action", store=False)
    
    issues_count = fields.Integer(compute="_issues_count",string="Issues", store=False)
    
    risk_count = fields.Integer(compute="_risk_count",string="Risks", store=False)

    ehs_count = fields.Integer(compute="_ehs_count",string="EHS", store=False)
    
    customer_picking_list_count = fields.Integer(compute="_picking_count",string="Picking List", store=False)

    change_request_count = fields.Integer(compute="_change_request_count",string="Change Request", store=False)

    decision_count = fields.Integer(compute="_decision_count",string="Decision", store=False)
    
    mo_count = fields.Integer(compute="_mo_count",string="Manufacturing Orders", store=False)
    
    parent_project_count = fields.Integer(compute="_parent_project_count",string="Parent Project(s)", store=False)
    
    crm_lead_id = fields.Many2one(comodel_name='crm.lead', string='Lead')
    
    parent_project_id = fields.Many2one(comodel_name='project.project', string='Parent Project')
    
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Acount', required=False, default=_default_analytic, track_visibility="always")
    account_id = fields.Many2one('account.account', string='Account',  domain = [('user_type_id', 'in', [5,8,17,16])])
    
    monthly_maintenance_schedule = fields.Datetime(string="Monthly Maintenance Schedule", track_visibility="onchange")
    client_site_visit = fields.Datetime(string="Client Site Visit", track_visibility="onchange")
    internal_external_monthly = fields.Date(string="Internal External Monthly", track_visibility="onchange")
    
    lead_technician_id = fields.Many2one(comodel_name='res.users', string='Lead Technician')
    quality_assurance_id = fields.Many2one(comodel_name='res.users', string='Quality Assurance Engineer')
    
    project_engineers_id = fields.Many2many(comodel_name='res.users', string='Project Team', help="list of engineeers for this project")
    
    project_plan_file = fields.Binary(string='Project Plan', track_visibility="onchange", store=True)
    project_budget = fields.Float(string='Project Budget', track_visibility="onchange", store=True, related='crm_lead_id.budget')
    
    project_code_id = fields.Many2one(comodel_name='res.partner', string='Project Code', help="Client sub account code")
    
    site_location_id = fields.Many2one(comodel_name='res.country.state', string='Site Location', related='site_code_id.state_id', domain=[('country_id.name','=','Nigeria')])
    #site_location_id = fields.Char(string='Site Location')
    
    site_code_id = fields.Many2one(comodel_name='site.code', string='Site Code')
    site_code_ids = fields.One2many(comodel_name='site.code', inverse_name='project_id', string='Site Code(s)')
    
    default_site_code = fields.Char(string='old Site Code') 
    
    client_type = fields.Many2one(comodel_name='customer.type', related='partner_id.customer_type_id', string='Customer Type')
    site_area = fields.Char(string='Site Area', related='site_code_id.site_area')
    site_address = fields.Char(string='Site Address')
    site_type = fields.Char(string='Site Type')
    region = fields.Char(string='Region', related='site_location_id.region')
    country_id = fields.Many2one(comodel_name='res.country', string="Country")
    project_status = fields.Char(string='Status')
    commissioning_date = fields.Date(string='Commissioning date')
    coordinates = fields.Char(string='Coordinates')
    
    type_of_offer = fields.Selection([('lease_to_own', 'Lease to own'), ('pass_battery', 'PaaS Battery'), ('paas_diesel', 'PaaS Diesel'),
                                      ('pass_diesel', 'PaaS Diesel'), ('solar', 'Solar Only'), ('saas', 'SaaS'), ('sale', 'Sale')], string='Service Type', required=False,default='saas')
    atm_power_at_night = fields.Selection([('yes', 'Yes'), ('no', 'No'),], string='Does the system power ATM night/we?', required=False,default='yes')
    
    pv_installed_capacity = fields.Float(string='Size (kWp) ')
    tariff_per_kwp = fields.Float(string='Tariff per kWh')
    total_capacity = fields.Float(string='Total Capacity (kWp)')
    solar_capacity = fields.Float(string='Solar Capacity (kWp)')
    
    new_currency_id = fields.Many2one(comodel_name="res.currency", string='Stored Currency', default=lambda self: self.env.user.company_id.currency_id.id, store=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', readonly=False)
    monthly_service_fees = fields.Float(string='Monthly Service fees')
    lease_duration = fields.Char(string='If lease, contract duration')
    sales_price = fields.Float(string="Sale Revenue")
    site_area = fields.Char(string='Site Area', related='site_code_id.site_area')
    
    '''
    @api.model
    def create(self, vals):
        site = self.env['site.location'].search([('id','=',vals['site_location_id'])])
        client = self.env['res.partner'].search([('id','=',vals['partner_id'])])
        code = client.client_code + site.code
        
        no = self.env['ir.sequence'].next_by_code('project.site.code')
        site_code = code + str(no)
        vals['default_site_code'] = site_code
        
        result = super(PurchaseOrder, self).create(vals)
        result.send_store_request_mail()
        return result
    '''
    
    '''
    @api.model
    def create(self, vals):
        site = self.env['res.country.state'].search([('id','=',vals['site_location_id'])])
        client = self.env['res.partner'].search([('id','=',vals['partner_id'])])
        if site and client:
            code = client.parent_account_number + "_" +  site.code
            
            no = self.env['ir.sequence'].next_by_code('project.site.code')
            site_code = code + "_" +  str(no)
            vals['default_site_code'] = site_code
        
        a = super(Project, self).create(vals)
        a.send_project_commencement_mail()
        return a
        return super(Project, self).create(vals)
    '''
    
    @api.onchange('crm_lead_id')
    def _onchange_partner_id(self):
        self.site_code_id = self.crm_lead_id.site_code_id
        self.site_area = self.crm_lead_id.site_area
        self.site_address = self.crm_lead_id.site_address
        self.site_type = self.crm_lead_id.site_type
        self.country_id = self.crm_lead_id.country_id
        self.lease_duration = self.crm_lead_id.contract_duration
        self.coordinates = self.crm_lead_id.coordinates
        self.type_of_offer = self.crm_lead_id.type_of_offer
        self.tariff_per_kwp = self.crm_lead_id.tariff_per_kwp
        self.site_location_id = self.crm_lead_id.site_location_id
        self.total_capacity = self.crm_lead_id.total_capacity
        self.solar_capacity = self.crm_lead_id.solar_capacity
        self.sales_price = self.crm_lead_id.sales_price
    
    @api.multi
    def send_project_commencement_mail(self):
        config = self.env['mail.template'].sudo().search([('name','=','Project')], limit=1)
        mail_obj = self.env['mail.mail']
        if config:
            values = config.generate_email(self.id)
            mail = mail_obj.create(values)
            if mail:
                mail.send()
    
    @api.multi
    def _checklist_count(self):
        oe_checklist = self.env['project.checklist']
        for pa in self:
            domain = [('project_id', '=', pa.id)]
            pres_ids = oe_checklist.search(domain)
            pres = oe_checklist.browse(pres_ids)
            checklist_count = 0
            for pr in pres:
                checklist_count+=1
            pa.checklist_count = checklist_count
        return True
    
    @api.multi
    def _action_count(self):
        oe_checklist = self.env['project.action']
        for pa in self:
            domain = [('project_id', '=', pa.id)]
            pres_ids = oe_checklist.search(domain)
            pres = oe_checklist.browse(pres_ids)
            action_count = 0
            for pr in pres:
                action_count+=1
            pa.action_count = action_count
        return True
    
    @api.multi
    def _mo_count(self):
        oe_checklist = self.env['mrp.production']
        for pa in self:
            domain = [('project_id', '=', pa.id)]
            pres_ids = oe_checklist.search(domain)
            pres = oe_checklist.browse(pres_ids)
            action_count = 0
            for pr in pres:
                action_count+=1
            pa.action_count = action_count
        return True
    
    @api.multi
    def _issues_count(self):
        oe_checklist = self.env['project.issues']
        for pa in self:
            domain = [('project_id', '=', pa.id)]
            pres_ids = oe_checklist.search(domain)
            pres = oe_checklist.browse(pres_ids)
            issues_count = 0
            for pr in pres:
                issues_count+=1
            pa.issues_count = issues_count
        return True
    
    @api.multi
    def _picking_count(self):
        oe_checklist = self.env['stock.picking']
        for pa in self:
                domain = [('partner_id', '=', pa.partner_id.id), ('picking_type_id', '=', 23)]
                pres_ids = oe_checklist.search(domain)
                pres = oe_checklist.browse(pres_ids)
                risk_count = 0
                for pr in pres:
                    risk_count+=1
                pa.customer_picking_list_count = risk_count
        return True
    
    @api.multi
    def _risk_count(self):
        oe_checklist = self.env['project.risk']
        for pa in self:
                domain = [('project_id', '=', pa.id)]
                pres_ids = oe_checklist.search(domain)
                pres = oe_checklist.browse(pres_ids)
                risk_count = 0
                for pr in pres:
                    risk_count+=1
                pa.risk_count = risk_count
        return True



    @api.multi
    def _change_request_count(self):
        oe_checklist = self.env['project.change_request']
        for pa in self:
                domain = [('project_id', '=', pa.id)]
                pres_ids = oe_checklist.search(domain)
                pres = oe_checklist.browse(pres_ids)
                change_request_count = 0
                for pr in pres:
                    change_request_count+=1
                pa.change_request_count = change_request_count
        return True

    @api.multi
    def _ehs_count(self):
        oe_checklist = self.env['project.ehs']
        for pa in self:
                domain = [('project_id', '=', pa.id)]
                pres_ids = oe_checklist.search(domain)
                pres = oe_checklist.browse(pres_ids)
                ehs_count = 0
                for pr in pres:
                    ehs_count+=1
                pa.ehs_count = ehs_count
        return True

    @api.multi
    def _decision_count(self):
        oe_checklist = self.env['project.decision']
        for pa in self:
                domain = [('project_id', '=', pa.id)]
                pres_ids = oe_checklist.search(domain)
                pres = oe_checklist.browse(pres_ids)
                decision_count = 0
                for pr in pres:
                    decision_count+=1
                pa.decision_count = decision_count
        return True
    
    @api.multi
    def _parent_project_count(self):
        oe_checklist = self.env['project.project']
        for pa in self:
                domain = [('id', '=', pa.id)]
                pres_ids = oe_checklist.search(domain)
                pres = oe_checklist.browse(pres_ids)
                parent_project_count = 0
                for pr in pres:
                    parent_project_count+=1
                pa.parent_project_count = parent_project_count
        return True
    
    
    @api.multi
    def open_project_checklist(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_project_checklist_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def open_project_action(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_project_actionform_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def open_project_issues(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_project_issuesform_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def open_manfacturing_order(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_mrp_production_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def open_project_change_request(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_project_change_request_form_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def open_project_risk(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_project_riskform_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action

    @api.multi
    def open_project_decision(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_project_decisionform_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action    

    @api.multi
    def open_project_ehs(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_project_ehsform_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def open_customer_picking_list(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_picking_list_form_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def open_parent_project(self):
        self.ensure_one()
        action = self.env.ref('project.open_view_project_all').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.partner_id.id))
        return action
    
    @api.multi
    def send_monthly_maintenance_schedule_mail(self):
        employees = self.env['project.project'].search([])
        current_dates = False
        for self in employees:
            if self.monthly_maintenance_schedule:
                
                current_dates = datetime.datetime.strptime(str(self.monthly_maintenance_schedule), "%Y-%m-%d")
                current_datesz = current_dates - relativedelta(days=5)
                
                date_start_day = current_datesz.day
                date_start_month = current_datesz.month
                date_start_year = current_datesz.year
                
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                test_today = datetime.datetime.today().strptime(today, "%Y-%m-%d")
                date_start_day_today = test_today.day
                date_start_month_today = test_today.month
                date_start_year_today = test_today.year
                
                if date_start_month == date_start_month_today:
                    if date_start_day == date_start_day_today:
                        if date_start_year == date_start_year_today:
                            config = self.env['mail.template'].sudo().search([('name','=','Monthly Maintenance Schedule')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
    
    @api.multi
    def send_client_site_visit_mail(self):
        employees = self.env['project.project'].search([])
        current_dates = False
        for self in employees:
            if self.client_site_visit:
                
                current_dates = datetime.datetime.strptime(str(self.client_site_visit), "%Y-%m-%d")
                current_datesz = current_dates - relativedelta(days=5)
                
                date_start_day = current_datesz.day
                date_start_month = current_datesz.month
                date_start_year = current_datesz.year
                
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                test_today = datetime.datetime.today().strptime(today, "%Y-%m-%d")
                date_start_day_today = test_today.day
                date_start_month_today = test_today.month
                date_start_year_today = test_today.year
                
                if date_start_month == date_start_month_today:
                    if date_start_day == date_start_day_today:
                        if date_start_year == date_start_year_today:
                            config = self.env['mail.template'].sudo().search([('name','=','Client Site Visit')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
                                    
    @api.multi
    def send_client_site_visit_customer_mail(self):
        employees = self.env['project.project'].search([])
        current_dates = False
        for self in employees:
            if self.client_site_visit:
                
                current_dates = datetime.datetime.strptime(str(self.client_site_visit), "%Y-%m-%d")
                current_datesz = current_dates - relativedelta(days=5)
                
                date_start_day = current_datesz.day
                date_start_month = current_datesz.month
                date_start_year = current_datesz.year
                
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                test_today = datetime.datetime.today().strptime(today, "%Y-%m-%d")
                date_start_day_today = test_today.day
                date_start_month_today = test_today.month
                date_start_year_today = test_today.year
                
                if date_start_month == date_start_month_today:
                    if date_start_day == date_start_day_today:
                        if date_start_year == date_start_year_today:
                            config = self.env['mail.template'].sudo().search([('name','=','Client Site Visit customer')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
                    
    @api.multi
    def send_internal_external_monthly_mail(self):
        employees = self.env['project.project'].search([])
        current_dates = False
        for self in employees:
            if self.internal_external_monthly:
                
                current_dates = datetime.datetime.strptime(str(self.internal_external_monthly), "%Y-%m-%d")
                current_datesz = current_dates - relativedelta(days=5)
                
                date_start_day = current_datesz.day
                date_start_month = current_datesz.month
                date_start_year = current_datesz.year
                
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                test_today = datetime.datetime.today().strptime(today, "%Y-%m-%d")
                date_start_day_today = test_today.day
                date_start_month_today = test_today.month
                date_start_year_today = test_today.year
                
                if date_start_month == date_start_month_today:
                    if date_start_day == date_start_day_today:
                        if date_start_year == date_start_year_today:
                            config = self.env['mail.template'].sudo().search([('name','=','Internal External Monthly')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
    
    @api.multi
    def create_purchase_agreement(self):
        """
        Method to open create purchase agreement form
        """

        partner_id = self.partner_id
        #client_id = self.client_id
        #store_request_id = self.id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('purchase_requisition', 'view_purchase_requisition_form')
        view_id = view_ref[1] if view_ref else False
        
        #purchase_line_obj = self.env['purchase.order.line']
        '''for subscription in self:
            order_lines = []
            for line in subscription.move_lines:
                order_lines.append((0, 0, {
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'account_analytic_id': 1,
                    'product_qty': line.product_uom_qty,
                    'schedule_date': date.today(),
                    'price_unit': line.product_id.standard_price,
                }))
        ''' 
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Purchase Agreement'),
            'res_model': 'purchase.requisition',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_type_id': 2, 'default_origin': self.name}
        }
        
        return res
    
    @api.multi
    def create_manufacturing_order(self):
        """
        Method to open create purchase agreement form
        """

        partner_id = self.partner_id
        #client_id = self.client_id
        #store_request_id = self.id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('mrp', 'mrp_production_form_view')
        view_id = view_ref[1] if view_ref else False
        
        #purchase_line_obj = self.env['purchase.order.line']
        '''for subscription in self:
            order_lines = []
            for line in subscription.move_lines:
                order_lines.append((0, 0, {
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'account_analytic_id': 1,
                    'product_qty': line.product_uom_qty,
                    'schedule_date': date.today(),
                    'price_unit': line.product_id.standard_price,
                }))
        ''' 
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
    
    
    @api.multi
    def create_store_request(self):
        """
        Method to open create purchase order form
        """

        #partner_id = self.request_client_id
        client_id = self.partner_id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('sunray', 'sunray_stock_form_view')
        view_id = view_ref[1] if view_ref else False
        
        #purchase_line_obj = self.env['purchase.order.line']
        #for subscription in self:
        #    order_lines = []
        #    for line in subscription.move_raw_ids:
        #        order_lines.append((0, 0, {
        #            'name': line.product_id.name,
        #            'product_uom': line.product_id.uom_id.id,
        #            'product_id': line.product_id.id,
        #            'reserved_availability': line.reserved_availability,
        #            'product_uom_qty': line.product_uom_qty,
        #            'additional': True,
        #            'date_expected': date.today(),
        #            'price_cost': line.product_id.standard_price,
        #       }))
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Store Request'),
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_origin': self.name, 'default_client_id': client_id.id, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id, 'default_partner_id': self.partner_id.id, 'default_project_id': self.id}
        }
        
        return res
    

class ProjectChecklist(models.Model):
    _name = "project.checklist"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    
    '''
    @api.multi
    def name_get(self):
        result = []
        for ticket in self:
            result.append((ticket.id, "%s (#%d)" % (ticket.ticket_id.name, ticket.id)))
        return result
    '''
    
    @api.model
    def _get_default_project(self):
        ctx = self._context
        if ctx.get('active_model') == 'project.project':
            return self.env['project.project'].browse(ctx.get('active_ids')[0]).id
  
    partner_id = fields.Many2one(comodel_name='res.partner', related='project_id.partner_id', string='Customer', readonly=True)
    
    project_id = fields.Many2one(comodel_name='project.project', string='Project', readonly=True, default=_get_default_project)
    
    detailed_site_review=fields.Boolean(
        string='Detailed site review'
    )
    detailed_system_design=fields.Boolean(
        string ='Detailed System design'
    )
    two_d_diagram=fields.Boolean(
        string="2D Diagram"
    )
    cable_schedule=fields.Boolean(
         string="Cable Schedule"
    )
    panel_layout=fields.Boolean(
        string="Panel Layout"
    )
    ancillary_equipment_breakdown=fields.Boolean(
        string="Ancillary Equipment breakdown"
    )
    
    project_schedule=fields.Boolean(
        string="Project Schedule"
    )
    purchase_stock_request_ancillaries_equipment=fields.Boolean(
         string="Purchase or stock request for ancillaries’ equipment"
    )
    
    project_planning_form = fields.Boolean(
        string='Project planning Form', 
    )
    
    communication_with_clients = fields.Boolean(
        string='Communication with clients', 
    )
    
    technician_assignment = fields.Boolean(
        string='Technician assignment', 
    )
    
    execution = fields.Boolean(
        string='Execution', 
    )
    
    quality_assurance = fields.Boolean(
        string='Quality Assurance', 
    )
    
    commissioning_test = fields.Boolean(
        string='Commissioning test', 
    )
    
    job_completion_certificate = fields.Boolean(
        string='Job Completion Certificate', 
    )
    
    training = fields.Boolean(
        string='Training', 
    )
    
    @api.multi
    def button_select_all(self):
        self.write({'detailed_site_review': True})
        self.write({'detailed_system_design': True})
        self.write({'two_d_diagram': True})
        self.write({'cable_schedule': True})
        self.write({'panel_layout': True})
        self.write({'ancillary_equipment_breakdown': True})
        self.write({'project_schedule': True})
        self.write({'purchase_stock_request_ancillaries_equipment': True})
        self.write({'project_planning_form': True})
        self.write({'communication_with_clients': True})
        self.write({'technician_assignment': True})
        self.write({'execution': True})
        self.write({'quality_assurance': True})
        self.write({'commissioning_test': True})
        self.write({'job_completion_certificate': True})
        self.write({'training': True})
        return {}
    

class ProjectAction(models.Model):
    _name = "project.action"
    _description = 'Project Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])
    
    @api.model
    def _get_default_project(self):
        ctx = self._context
        if ctx.get('active_model') == 'project.project':
            return self.env['project.project'].browse(ctx.get('active_ids')[0]).id
  
    partner_id = fields.Many2one(comodel_name='res.partner', related='project_id.partner_id', string='Customer', readonly=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', readonly=True, default=_get_default_project)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Owner', default=_default_employee)
    state = fields.Selection([
        ('draft', 'New'),
        ('wip', 'Wip'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ('open', 'Open'),
        ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    project_action_priority = fields.Selection([('0', '0'),('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Urgent')], string='Priority', required=False)
    project_action_line_ids = fields.One2many('project.action.line', 'project_action_id', string="Action Move", copy=True)
    due_date = fields.Date(string='Due Date')
    
    
class ProjectActionLine(models.Model):
    _name = "project.action.line"
    _description = 'Project Action Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    project_action_id = fields.Many2one('project.action', 'Project Action')
    s_n = fields.Float(string='S/N', compute='_total_cost', readonly=False)
    action_items = fields.Char(string='Action Item')
    comments = fields.Char(string='Comments')
    
    def _total_cost(self):
        s_n = 1
        for a in self:
            s_n +=1
            a.s_n = s_n
        
class ProjectIssue(models.Model):
    _name = "project.issues"
    _description = 'Project Issues'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])
    
    @api.model
    def _get_default_project(self):
        ctx = self._context
        if ctx.get('active_model') == 'project.project':
            return self.env['project.project'].browse(ctx.get('active_ids')[0]).id
        
    name = fields.Char(string='Issue Title', required=True)
    description = fields.Char(string='Issue Description')
    partner_id = fields.Many2one(comodel_name='res.partner', related='project_id.partner_id', string='Customer', readonly=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', readonly=True, default=_get_default_project)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Reported By', default=_default_employee)
    state = fields.Selection([
        ('draft', 'New'),
        ('wip', 'Wip'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ('open', 'Open'),
        ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    project_issue_severity = fields.Selection([('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Urgent')], string='Severity', required=False)
    project_action_priority = fields.Selection([('0', '0'),('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Urgent')], string='Priority', required=False)
    date = fields.Date(string='Reported On', default=date.today())
    comments = fields.Char(string='Comments')
    
class ProjectRisk(models.Model):
    _name = "project.risk"
    _description = 'Project Risk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])
    
    @api.model
    def _get_default_project(self):
        ctx = self._context
        if ctx.get('active_model') == 'project.project':
            return self.env['project.project'].browse(ctx.get('active_ids')[0]).id
    
    state = fields.Selection([
        ('draft', 'New'),
        ('wip', 'Wip'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ('open', 'Open'),
        ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    partner_id = fields.Many2one(comodel_name='res.partner', related='project_id.partner_id', string='Customer', readonly=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', readonly=True, default=_get_default_project)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Owner', default=_default_employee)
    project_risk_line_ids = fields.One2many('project.risk.line', 'project_risk_id', string="Project Risk", copy=True)

class ProjectRiskLine(models.Model):
    _name = "project.risk.line"
    _description = 'project Risk Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    project_risk_id = fields.Many2one ('project.risk', 'Project Risk')
    risk_title = fields.Char(string='Risk Title')
    risk_impact = fields.Char(string='Risk Description/Impact')
    risk_status = fields.Selection([
        ('new','New'),
        ('wip','WIP'),
        ('closed', 'Closed'), 
        ('on hold', 'On Hold'),
        ('open', 'Open'),
        ], string = 'Status', track_visibility='onchange')
    employee_id = fields.Many2one(comodel_name='project.risk')
    date = fields.Date(string='Identified Date')
    risk_category = fields.Selection([
        ('project', 'Project'),
        ('organizational', 'Organizational'),
        ('resource','Resource'),
        ('environment','Environment'), 
        ], string = 'Risk Categories', track_visibility='onchange')
    mitigation= fields.Char(string='Possible Mitigation')
    date_closed = fields.Date(string='Date Closed')

class ProjectEHS(models.Model):
    _name = "project.ehs"
    _description = 'Project EHS'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])

    @api.model
    def _get_default_project(self):
        ctx = self._context
        if ctx.get('active_model') == 'project.project':
            return self.env['project.project'].browse(ctx.get('active_ids')[0]).id
        
    project_ehs_name = fields.Char(string='Issue Title', required=True)
    project_ehs_description = fields.Char(string='Issue Description')
    partner_id = fields.Many2one(comodel_name='res.partner', related='project_id.partner_id', string='Customer', readonly=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', readonly=True, default=_get_default_project)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Reported By', default=_default_employee)
    project_ehs_state = fields.Selection([
        ('draft', 'New'),
        ('wip', 'Wip'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ('open', 'Open'),
        ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    project_ehs_severity = fields.Selection([('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Critical')], string='Severity', required=False)
    project_ehs_priority = fields.Selection([('0', '0'),('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Urgent')], string='Priority', required=False)
    date = fields.Date(string='Reported On', default=date.today())
    comments = fields.Char(string='Comments')


class ProjectDecisions(models.Model):
    _name = "project.decision"
    _description = 'Project Decision'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])

    @api.model
    def _get_default_project(self):
        ctx = self._context
        if ctx.get('active_model') == 'project.project':
            return self.env['project.project'].browse(ctx.get('active_ids')[0]).id
        
    decision_detail = fields.Char(string='Decision Details', required=True)
    decision_impact = fields.Char(string='Decision Impact')
    staff_id = fields.Char(comodel_name='hr.employee', string = 'Proposed by')
    partner_id = fields.Many2one(comodel_name='res.partner', related='project_id.partner_id', string='Customer', readonly=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', readonly=True, default=_get_default_project)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Approved By', default=_default_employee)
    project_decision_state = fields.Selection([
        ('draft', 'New'),
        ('wip', 'Wip'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ('open', 'Open'),
        ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    date = fields.Date(string='Date', default=date.today())
    comments = fields.Char(string='Resulting Actions/Comments')


class ProjectChangeRequest(models.Model):
    _name = 'project.change_request'
    _description = 'Project Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])

    @api.model
    def _get_default_project(self):
        ctx = self._context
        if ctx.get('active_model') == 'project.project':
            return self.env['project.project'].browse(ctx.get('active_ids')[0]).id
        
    state = fields.Selection([
        ('draft', 'New'),
        ('submit', 'Submited'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    partner_id = fields.Many2one(comodel_name='res.partner', related='project_id.partner_id', string='Customer', readonly=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', readonly=True, default=_get_default_project)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Requester', default=_default_employee)
    date = fields.Date(string='Date Raised', default=date.today())
    project_change_request_priority = fields.Selection([('0', '0'),('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Urgent')], string='Priority', required=False)
    project_change_request_line_ids = fields.One2many('project.change_request.line', 'project_change_request_id', string="Request Move", copy=True)
    
    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return {}
    
    @api.multi
    def button_hold(self):
        self.write({'state': 'on_hold'})
        subject = "Change request for {} is on hold".format(self.project_id.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_close(self):
        self.write({'state': 'closed'})
        subject = "Change request for {} has been Closed".format(self.project_id.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        group_id = self.env['ir.model.data'].xmlid_to_object('project.group_project_manager')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "A Change request has been made for this '{}' project".format(self.project_id.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
        return {}
    
    @api.multi
    def button_approve(self):
        self.write({'state': 'approved'})
        subject = "Change request {} has been Approved".format(self.project_id.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def button_reject(self):
        self.write({'state': 'rejected'})
        subject = "Change request {} has been Rejected".format(self.project_id.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
class ProjectChangeRequestLine(models.Model):
    _name = "project.change_request.line"
    _description = 'Project Action Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    project_change_request_id = fields.Many2one('project.change_request', 'Project Change Request')
    s_n = fields.Float(string='S/N', readonly=False)
    project_change_request_description = fields.Char(string='Change Description')
    project_change_request_severity = fields.Selection([('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Critical')], string='Severity', required=False)
    project_change_request_priority = fields.Selection([('0', '0'),('1', 'Low'), ('2', 'Medium'), ('3', 'High'), ('4', 'Urgent')], string='Priority', required=False)
    comments = fields.Char(string='Comments')
