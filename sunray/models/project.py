from datetime import date
from odoo import models, fields, api, _


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
