from odoo import models, fields, api, _
    
    
class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['purchase.order']
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.partner_ref = self.partner_id.ref
        
    @api.onchange('requisition_id')
    def _onchange_partner_id(self):
        self.employee_id = self.requisition_id.employee_id
    
    @api.multi
    def _check_line_manager(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if current_employee == self.employee_id:
            raise UserError(_('You are not allowed to approve your own request.'))
        
    @api.multi
    def _check_manager_position(self):
        current_manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return current_manager.job_id.name
    
    @api.multi
    def _check_vendor_registration(self):
        return True
    
    def _default_employee(self):
        if self.requisition_id:
            return self.requisition_id.employee_id.id
        else:
            return self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1)
    
    @api.multi
    def _check_override(self):
        for self in self:
            for line in self.order_line:
                if line.need_override and line.override_budget == False:
                    self.need_override = True
                else:
                    self.need_override = False
    
    @api.depends('amount_total')
    def _check_approval(self):
        if self.amount_total > 10.00:
            self.need_management_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_sale_account_budget')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "RFQ {} needs management approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_approval = False
    
    @api.multi
    def _compute_amount_in_word(self):
        for rec in self:
            rec.num_word = str(rec.currency_id.amount_to_text(rec.amount_total)) + ' only'

    num_word = fields.Char(string="Amount In Words:", compute='_compute_amount_in_word')
    
    need_override = fields.Boolean ('Need Budget Override', compute= "_check_override", track_visibility="onchange", copy=False)
    
    employee_id = fields.Many2one('hr.employee', 'Employee',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, default=_default_employee)
    request_date = fields.Date(string='Request Date', readonly=True, track_visibility='onchange')
    department_name = fields.Char(string="Employee Department", related="employee_id.department_id.name", readonly=True)    
    
    approval_date = fields.Date(string='Manager Approval Date', readonly=True, track_visibility='onchange')
    manager_approval = fields.Many2one('res.users','Manager Approval Name', readonly=True, track_visibility='onchange')
    manager_position = fields.Char('Manager Position', track_visibility='onchange')
    
    second_manager_approval_date = fields.Date(string='Manager Approval Date', readonly=True, track_visibility='onchange')
    second_manager_approval = fields.Many2one('res.users','Manager Approval Name', readonly=True, track_visibility='onchange')
    second_manager_position = fields.Char('2nd Manager Position', track_visibility='onchange')
    
    finance_manager_approval_date = fields.Date(string='Finance Approval Date', readonly=True, track_visibility='onchange')
    finance_manager_approval = fields.Many2one('res.users','Finance Approval Name', readonly=True, track_visibility='onchange')
    finance_manager_position = fields.Char('Finance Personnel Position', track_visibility='onchange')    
    
    po_approval_date = fields.Date(string='Authorization Date', readonly=True, track_visibility='onchange')
    po_manager_approval = fields.Many2one('res.users','Manager Authorization Name', readonly=True, track_visibility='onchange')
    po_manager_position = fields.Char('Manager Authorization Position', track_visibility='onchange')
    
    line_manager_approval_date = fields.Date(string='Line-Manager Approval Date', readonly=True, track_visibility='onchange')
    line_manager_approval = fields.Many2one('res.users','Line-Manager Approval Name', readonly=True, track_visibility='onchange')
    parent_po = fields.Many2one('purchase.order','Parent PO', track_visibility='onchange')
    client_id = fields.Many2one('res.partner','Client', track_visibility='onchange')
    
    project_id = fields.Many2one(comodel_name='project.project', string='Project')
    
    inform_budget_owner = fields.Boolean ('Inform Budget Owner', track_visibility="onchange", copy=False)
    need_finance_review = fields.Boolean ('Finance Review', track_visibility="onchange", copy=False)
    need_finance_review_done = fields.Boolean ('Finance Review Done', track_visibility="onchange", copy=False)
    finance_review_done = fields.Boolean ('Finance Review Done', track_visibility="onchange", copy=False)
    
    need_management_approval = fields.Boolean(string="Management Approval")
    need_first_management_approval = fields.Boolean(string="Management Approval 1")
    need_second_management_approval = fields.Boolean(string="Management Approval 2")
    
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('submit', 'Manager To Approve'),
        ('manager_approve', 'Procurement To Approve'),
        ('procurement_approve', 'CFO To Approve'),
        ('cfo_approve', 'COO To Approve'),
        ('coo_approve', 'CEO To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    
    stock_source = fields.Char(string='Source document')
    store_request_id = fields.Many2one('stock.picking','Store Request', readonly=True, track_visibility='onchange')
    
    @api.model
    def create(self, vals):
        result = super(PurchaseOrder, self).create(vals)
        result.send_store_request_mail()
        return result
    
    @api.multi
    def send_store_request_mail(self):
        if self.store_request_id:
            config = self.env['mail.template'].sudo().search([('name','=','P.O Store Request')], limit=1)
            mail_obj = self.env['mail.mail']
            if config:
                values = config.generate_email(self.id)
                mail = mail_obj.create(values)
                if mail:
                    mail.send()
    
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        self.request_date = date.today()
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_hr_line_manager')
        user_ids = []
        partner_ids = []
        if self.employee_id.parent_id.user_id:
            partner_ids.append(self.employee_id.parent_id.user_id.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "RFQ '{}' needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return True
                    
    @api.multi
    def action_line_manager_approval(self):
        self.write({'state':'manager_approve'})
        self.line_manager_approval_date = date.today()
        self.line_manager_approval = self._uid
        subject = "RFQ {} has been approved by Line Manager".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        self.notify_procurement_for_approval()
    
    @api.multi
    def action_procurement_approval(self):
        self.write({'state':'management'})
        self.po_approval_date = date.today()
        self.po_manager_approval = self._uid
        self.po_manager_position = self._check_manager_position()
        self.button_request_finance_review()
        subject = "RFQ {} has been approved by Procurement".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def notify_procurement_for_approval(self):
        group_id = self.env['ir.model.data'].xmlid_to_object('purchase.group_purchase_manager')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "RFQ {} needs approval from procurement".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.depends('amount_total')
    def check_manager_approval_one(self):
        company_currency = self.company_id.currency_id
        current_currency = self.currency_id
        self.need_management_approval = 
        if self.amount_total < 100000.00:
            self.need_first_management_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_below_1st_authorization')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "RFQ {} needs your approval, Below Quota".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_management_approval = False
            
    @api.depends('amount_total')
    def check_manager_approval_two(self):
        if self.amount_total > 100000.00:
            self.need_first_management_approval = True
            self.need_second_management_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_above_1st_authorization','sunray.group_below_1st_authorization')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "RFQ {} needs your approval, Above Quota".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_management_approval = False
  
    @api.multi
    def notify_secondpoapproval_for_approval(self):
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_above_1st_authorization')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "RFQ {} needs your approval, Above Quota".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def button_submit_legal(self):
        self.write({'state': 'legal'})
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_legal_team')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Purchase Order {} needs a review from legal team".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
    
    @api.multi
    def button_finance_reviewd(self):
        self.need_finance_review_done = True
        self.finance_manager_approval_date = date.today()
        self.finance_manager_approval = self._uid
        self.finance_manager_position = self._check_manager_position()
        subject = "Finance Review has been Done".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        if self.amount_total < 100000.00:
            self.check_manager_approval_one()
        elif self.amount_total > 100000.00:
            self.check_manager_approval_two()
    
    @api.multi
    def _check_budget(self):
        override = False
        for line in self.order_line:
            self.env.cr.execute("""
                    SELECT * FROM crossovered_budget_lines WHERE
                    general_budget_id in (SELECT budget_id FROM account_budget_rel WHERE account_id=%s) AND
                    analytic_account_id = %s AND 
                    to_date(%s,'yyyy-mm-dd') between date_from and date_to""",
                    (line.account_id.id,line.account_analytic_id.id, line.order_id.date_order))
            result = self.env.cr.fetchone()
            if result:
                result = self.env['crossovered.budget.lines'].browse(result[0])  
                if line.price_total > result.allowed_amount and line.override_budget == False:
                    override = True
                    line.write({'need_override': True})
            else:
                if line.override_budget == False:
                    override = True
                    line.write({'need_override': True})
        if override:
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_hr_line_manager')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Purchase Order {} needs a budget override".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        return True

    @api.multi
    def button_confirm(self):
        for order in self:
            if order.state not in ['draft','submit', 'sent', 'management']:
                continue
            #self._check_line_manager()
            self._check_line_manager()
            #self._check_approval()
            #self.button_submit_legal()
            #if self._check_budget() == False and self.need_override:
             #   return {}
            self.approval_date = date.today()
            self.manager_approval = self._uid
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.user.company_id.currency_id.compute(order.company_id.po_double_validation_amount, order.currency_id)):
                    #or order.user_has_groups('purchase.group_purchase_manager'):
                #order.button_approve()
                print("don't confirm po even with po manager access")
                order.write({'state': 'manager_approve'})
            else:
                order.write({'state': 'manager_approve'})
        return True
    
    @api.multi
    def action_first_manager_approval(self):
        if self.need_first_management_approval == True: 
            self.approval_date = date.today()
            self.manager_approval = self._uid
            self.manager_position = self._check_manager_position()
            if self.need_second_management_approval == False:
                self.button_approve()
        subject = "RFQ {} has been approved".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        self.need_first_management_approval = False
        
    @api.multi
    def action_second_manager_approval(self):
        if self.need_second_management_approval == True: 
            self.second_manager_approval_date  = date.today()
            self.second_manager_approval  = self._uid
            self.second_manager_position = self._check_manager_position()
            self.button_approve()
        subject = "RFQ {} has been approved".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def button_approve(self):
        res = super(PurchaseOrder, self).button_approve()
        self._check_vendor_registration()
        self._check_line_manager()
        return res
    
    @api.multi
    def button_approve_without_authorization(self):
        res = super(PurchaseOrder, self).button_approve()
        return res
    
    @api.multi
    def button_request_finance_review(self):
        #self.write({'state': 'approve'})
        self.need_finance_review = True
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_po_finance')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This RFQ '{}' needs review from Finance".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_inform_budget_owner(self):
        #self.write({'state': 'approve'})
        self.inform_budget_owner = True
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_sale_account_budget')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This RFQ {} needs your attention".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_finance_review_done(self):
        self.finance_review_done = True
        subject = "Finance review has been Done, Purchase Order {} can be confirmed now".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    #NOT TO BE USED YET AND DO NOT DELETE THIS 
    """@api.multi
    def button_approve(self):
        super(PurchaseOrder, self).button_approve()
        for order in self:
            for order_line in order.order_line:
                order_line.product_id.standard_price = order_line.price_unit
    """

    
    @api.multi
    def button_reset(self):
        self.mapped('order_line')
        self.write({'state': 'draft'})
        return {}
    
    
class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ['purchase.order.line']
    
    def _default_analytic(self):
        return self.env['account.analytic.account'].search([('name','=','sunray')])
    
    def _default_account(self):
        return self.product_id.property_account_expense_id
    
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True, track_visibility="onchange")
    account_id = fields.Many2one('account.account', string='Account',  domain = [('user_type_id', 'in', [5,8,17,16])])
    need_override = fields.Boolean ('Need Budget Override', track_visibility="onchange", copy=False)
    override_budget = fields.Boolean ('Override Budget', track_visibility="onchange", copy=False)
    
    specification = fields.Char(string='Specification')
    part_no = fields.Char(string='Part No')
    item_type = fields.Selection([
        ('fixed_asset', 'Fixed Asset'),
        ('inventory', 'Inventory'),
        ('maintanance', 'Maintanance'),
        ('supplies', 'Supplies'),
        ('others', 'Others'),
        ], string='Item type')
    
    @api.multi
    def action_override_budget(self):
        self.write({'override_budget': True})
        if self.order_id.need_override == False:
            subject = "Budget Override Done, Purchase Order {} can be approved now".format(self.name)
            partner_ids = []
            for partner in self.order_id.message_partner_ids:
                partner_ids.append(partner.id)
            self.order_id.message_post(subject=subject,body=subject,partner_ids=partner_ids)