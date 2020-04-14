# -*- coding: utf-8 -*-
import datetime

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import email_split, float_is_zero
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
import traceback
import sys
from odoo.addons import decimal_precision as dp

WHITE_LIST = ['odooprojects']      # Look for these words in the file path.
EXCLUSIONS = ['']          # Ignore <listcomp>, etc. in the function name.


PURCHASE_REQUISITION_STATES = [
    ('draft', 'Draft'),
    ('submit', 'Submitted'),
    ('approve', 'Approved'),
    ('ongoing', 'Ongoing'),
    ('in_progress', 'Confirmed'),
    ('open', 'Bid Selection'),
    ('done', 'Closed'),
    ('cancel', 'Cancelled')
]

class ResCompany(models.Model):
    _inherit = "res.company"
    
    company_lead_approval = fields.Boolean(string='Lead Approval', company_dependent=True)
    
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    lead_approval = fields.Boolean(string='Lead Approval', company_dependent=False, readonly=False, related='company_id.company_lead_approval')

class IrSequence(models.Model):
    _inherit = 'ir.sequence'
    
    @api.multi
    def _check_po_sequence(self):
        po_code = self.env['ir.sequence'].search([('code', '=', 'purchase.order')], limit=1)
        if po_code:
            po_code.number_next_actual = 1
    
class Partners(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('validate', 'Second Approval'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice address'),
         ('delivery', 'Shipping address'),
         ('other', 'Sub Account'),
         ("private", "Private Address"),
        ], string='Address Type',
        default='contact',
        help="Used by Sales and Purchase Apps to select the relevant address depending on the context.")
    
    name = fields.Char(index=True, track_visibility="onchange")
    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks', track_visibility="onchange")
    email = fields.Char(track_visibility="onchange")
    
    tax_compliance = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Tax compliance', required=False)
    due_diligence_form = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Due Diligence Form', required=False)
    cac = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='CAC', required=False)
    delivery_speed = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Delivery Speed')
    
    overall_vendor_rating = fields.Selection([('0', '0'),('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Overall Vendor Rating', required=False)
    
    parent_account_number = fields.Char(string='Customer Code', required=False, index=True, copy=False, store=True)
    
    #client_code = fields.Char(string='Client Code', required=False, index=True, copy=False, store=True)
    
    vendor_registration = fields.Boolean ('Vendor fully Registered', track_visibility="onchange", readonly=True)
    customer_registration = fields.Boolean ('Customer fully Registered', track_visibility="onchange", readonly=True)
    
    tin = fields.Char(string='Tin', required=False, index=True, copy=False, store=True)
    wht_rate = fields.Float(string='WHT Rate', required=False, index=True, copy=False, store=True)
    transaction_class = fields.Selection([('suply', 'Supply'),('service', 'Service'), ('contract', 'Contract'), ('licencing', 'Licencing'), ('rent', 'Rent'), ('prof', 'Professional/Consultancy service')], string='Transaction Class', required=False, index=True, copy=False, store=True)
    transaction_authority = fields.Char(string='Tax Authoritiy', required=False, index=True, copy=False, store=True)
    iban = fields.Char(string='IBAN', required=False, index=True, copy=False, store=True)
    transaction_description = fields.Char(string='Transaction Description', required=False, index=True, copy=False, store=True)
    
    site_code_count = fields.Integer(compute="_site_code_count",string="Site Code(s)", store=False)
    
    #futher Vendor details
    building_no = fields.Char(string="Building No.")
    office_no = fields.Char(string="Office No.")
    postal_code = fields.Char(string="Postal Code")
    district = fields.Char(string="District/ Region")
    
    rc = fields.Char(string="RC or Business registration number")
    vat_eligible = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="VAT eligibility")
    business_legal_structure = fields.Selection([('joint', 'Joint Stock Company'), ('limited', 'Limited Liability Company'), ('non', 'Non-Profit organization'), ('public', 'Public Liability Company'), ('trust', 'Business Trust'), ('other', 'Other')], 
                                                string="Business Legal Structure")
    vat_no = fields.Char(string="Vat No")
    tax_no = fields.Char(string="Tax No.")
    legal = fields.Char(string="Other, Please specify:")
    
    customer = fields.Boolean(string='Is a Customer', default=False,
                               help="Check this box if this contact is a customer. It can be selected in sales orders.")
    
    potential_customer = fields.Boolean(string='Potential Customer', default=False,
                                        help="Check this box if this contact is a potential customer. It can be selected in sales orders.")
    
    employee = fields.Boolean(string='Employee')
    
    daystar_companies = fields.Boolean(string='Daystar Companies')
    
    stored_display_name = fields.Char(string="stored_display_name")
    
    customer_type_id = fields.Many2one(comodel_name='customer.type', string='Customer Type')
    
    #_sql_constraints = [('section_parent_account_number', 'UNIQUE(parent_account_number)', 'Customer Code must be Unique')]
    
    
    ''' 
    @api.multi
    def _check_customer_code(self):
        customer_code = self.env['res.partner'].search([('parent_account_number', '=', self.parent_account_number)], limit=1)
        if customer_code.parent_account_number == self.parent_account_number:
            raise UserError(_('Customer Code Already Exists'))
    
    @api.model
    def create(self, vals):
        #if vals.get('name', 'New') == 'New':
         #   vals['name'] = self.env['ir.sequence'].next_by_code('availability.request') or '/'
        customer_code = self.env['res.partner'].search([('parent_account_number', '=', self.parent_account_number)], limit=1)
        if customer_code.parent_account_number == vals['parent_account_number']:
            #raise ValidationError(_('Customer Code Already Exists'))
            print('customer code,', customer_code)
        return super(Partner, self).create(vals)
    '''
        
    '''
    @api.onchange('name')
    def _onchange_name(self):
        subject = "Store request {} has been approved and validated".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    '''
    '''
    @api.onchange('customer')
    def _onchange_customer(self):
        if self.customer == True:
            self.potential_customer = True
            self.customer = False
    '''
    @api.multi
    def _site_code_count(self):
        oe_checklist = self.env['site.code']
        for pa in self:
            domain = [('partner_id', '=', pa.id)]
            pres_ids = oe_checklist.search(domain)
            pres = oe_checklist.browse(pres_ids)
            issues_count = 0
            for pr in pres:
                issues_count+=1
            pa.site_code_count = issues_count
        return True
    
    '''
    @api.model
    def create(self, vals):
        if 'customer' in vals and vals['customer'] == True and vals['parent_id'] == False:
            vals['parent_account_number'] = self.env['ir.sequence'].next_by_code('res.partner') or '/'
        elif 'customer' in vals and vals['customer'] == True and vals['type'] == 'other':
                vals['parent_account_number'] = self.env['ir.sequence'].next_by_code('res.partner.sub') or '/'
        elif 'supplier' in vals and vals['supplier'] == True and vals['parent_id'] == False:
                vals['ref'] = self.env['ir.sequence'].next_by_code('res.partner.vendor') or '/'        
        return super(Partner, self).create(vals)
    '''
    
#     @api.multi
#     def _check_customer_code(self, vals):
#         customer = self.env['res.partner'].search([('parent_account_number','=',vals['parent_account_number'])])
#         if vals['parent_account_number'] == False:
#             print('proceed')
#         else:
#             if customer:
#                 raise UserError(_('Customer Code Must Unique!'))
    
    @api.multi
    def _check_potential_customer(self, vals):
        if 'potential_customer' in vals and vals['potential_customer'] == True:
            if not self.user_has_groups('sunray.group_potential_customer_creation'):
                raise UserError(_("Only Members of the BD/Sales team can create Potential Customer(s)"))
            else:
                print('nothing')
    
    @api.multi
    def _check_customer_code(self, vals):
        customer_code = self.env['res.partner'].search([('parent_account_number','=',vals['parent_account_number'])])
        if customer_code:
            raise UserError(_('Customer Code Already Exists!'))
    
    @api.model
    def create(self, vals):
        self._check_customer_code(vals)
        self._check_potential_customer(vals)
        return super(Partners, self).create(vals)
    
    ''' 
    @api.multi
    def write(self, vals):
        self._check_customer_code(vals)
        return super(Partner, self).write(vals)
    '''
    
    @api.multi
    def name_get(self):
        res = []
  
        for partner in self:
            result = partner.name
            if partner.parent_account_number:
                result = str(partner.name) + " " + str(partner.parent_account_number)
            res.append((partner.id, result))
        return res
    
    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return {}
    
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_one_vendor_approval')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This Vendor {} needs first approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_validate(self):
        self._check_line_manager()
        self.write({'state': 'validate'})
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_two_vendor_approval')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This Vendor {} needs second approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_approve(self):
        self.write({'state': 'approve'})
        self.vendor_registration = True
        return {}
    
    @api.multi
    def button_reject(self):
        self.write({'state': 'reject'})
        return {}
    
    #this is the vendor checklist
    completed_vendor_information = fields.Boolean(string="COMPLETED VENDOR INFORMATION FORM (AS  ATTACHED)")
    report_of_proposers_follow_up = fields.Boolean(string="REPORT OF PROPOSER'S FOLLOW UP REVIEW OF SECTIONS 4 & 5")
    true_copy_incorporation = fields.Boolean(string="COPY OF CERTIFICATE OF INCORPORATION / BUSINESS NAME REGISTRATION CERTIFICATE")
    true_copy_memorandum = fields.Boolean(string="CERTIFIED TRUE COPY OF MEMORANDUM AND ARTICLE OF  ASSOCIATION FOR LIMITED LIABILITY COMPANIES")
    true_copy_form_c02 = fields.Boolean(string="CERTIFIED TRUE COPY OF FORM C02 AND C07 FOR LIMITED LIABILITY COMPANIES")
    Vat_cert = fields.Boolean(string="VAT CERTIFICATE / FIRS REGISTRATION CERTIFICATE")
    sign_and_stamp = fields.Boolean(string="SIGN AND STAMP THE FOLLOWING SUNRAY VENRURES GENERAL TERMS & CONDITIONS BY AUTHORIZED STAFF")

    current_dpr = fields.Boolean(string="CURRENT DPR CERTIFICATE (If Applicable)")
    commercial_certificate = fields.Boolean(string="COMMERCIAL PROPOSAL OR WEBSITE REVIEW (COMPANY PROFILE INCLUDING DETAILS OF MANAGEMENT TEAM, REFERENCES & CASE STUDIES)")
    proposers_report = fields.Boolean(string="PROPOSER'S REPORT CONFIRMING CLEAN REVIEW ON INTERNET & OTHER AVAILABLE SOURCES (IF NOT CLEAN, FURTHER INFORMATION ON MATTERS IDENTIFIED)")
    copies_of_required_specialist = fields.Boolean(string="COPIES OF REQUIRED SPECIALIST CERTIFICATIONS, REGISTRATIONS & LICENCES (If Applicable)")

    recommendation_letters_from_applicant = fields.Boolean(string="RECOMMENDATION LETTER FROM APPLICANT BANKERS IN RESPECT TO THE OPERATION OF HIS/HER COMPANY'S ACCOUNT")
    evidence_of_tax = fields.Boolean(string="EVIDENCE OF TAX PAYMENT")
    code_of_conduct = fields.Boolean(string="CODE OF CONDUCT AND CODE OF ETHICS - SIGNED BY THE COMPANY'S MD OR AUTHORIZED STAFF")
    specific_references = fields.Boolean(string="SPECIFIC REFERENCES")
    latest_financials = fields.Boolean(string="LATEST FINANCIAL STATEMENTS / KEY KPIs")
    
    completed_customer_information = fields.Boolean(string="COMPLETED CUSTOMER INFORMATION FORM (AS  ATTACHED)")
    
    @api.multi
    def button_select_all(self):
        self.write({'completed_vendor_information': True})
        self.write({'report_of_proposers_follow_up': True})
        self.write({'true_copy_incorporation': True})
        self.write({'true_copy_memorandum': True})
        self.write({'true_copy_form_c02': True})
        self.write({'Vat_cert': True})
        self.write({'sign_and_stamp': True})
        self.write({'current_dpr': True})
        self.write({'commercial_certificate': True})
        self.write({'proposers_report': True})
        self.write({'copies_of_required_specialist': True})
        self.write({'evidence_of_tax': True})
        self.write({'recommendation_letters_from_applicant': True})
        self.write({'code_of_conduct': True})
        self.write({'specific_references': True})
        self.write({'latest_financials': True})
        return {}
    
    @api.multi
    def open_customers_site_code(self):
        self.ensure_one()
        action = self.env.ref('sunray.site_location_action_window').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.id))
        return action

class CustomerType(models.Model):
    _name = "customer.type"
    _description = 'Customer Type'
    
    name = fields.Char(string='Name', required=True)

class HrExpense(models.Model):
    _name = "hr.expense"
    _inherit = "hr.expense"
    
    
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', states={'post': [('readonly', True)], 'done': [('readonly', True)]}, oldname='analytic_account', required=True)
    
class HrExpenseSheet(models.Model):
    _name = "hr.expense.sheet"
    _inherit = 'hr.expense.sheet'
    
    state = fields.Selection([('submit', 'Submitted'),
                              ('approve', 'Line Manager Approved'),
                              ('confirmed', 'MD Approved'),
                              ('post', 'Posted'),
                              ('open', 'Open'),
                              ('done', 'Paid'),
                              ('cancel', 'Refused')
                              ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='submit', required=True,
    help='Expense Report State')
    
    @api.multi
    def button_md_approval(self):
        self.write({'state': 'confirmed'})
        return {}
    
    @api.multi
    def expense_md_approval_notification(self):
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_md')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Expense '{}' needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
    
    @api.multi
    def approve_expense_sheets(self):
        if not self.user_has_groups('hr_expense.group_hr_expense_user'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own expenses"))

            if not self.env.user in current_managers:
                raise UserError(_("You can only approve your department expenses"))

        responsible_id = self.user_id.id or self.env.user.id
        self.write({'state': 'approve', 'user_id': responsible_id})
        self.activity_update()
        self.expense_md_approval_notification()
    
    @api.multi
    def action_sheet_move_create(self):
        if any(sheet.state != 'confirmed' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))

        expense_line_ids = self.mapped('expense_line_ids')\
            .filtered(lambda r: not float_is_zero(r.total_amount, precision_rounding=(r.currency_id or self.env.user.company_id.currency_id).rounding))
        res = expense_line_ids.action_move_create()

        if not self.accounting_date:
            self.accounting_date = self.account_move_id.date

        if self.payment_mode == 'own_account' and expense_line_ids:
            self.write({'state': 'post'})
        else:
            self.write({'state': 'done'})
        self.activity_update()
        return res

class BudgetDept(models.Model):
    _name = 'account.budget.post'
    _inherit = 'account.budget.post'
    
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string='Department')

class CrossoveredBudgetLines(models.Model):
    _name = "crossovered.budget.lines"
    _inherit = ['crossovered.budget.lines']
    _order = "general_budget_id"
    
    allowed_amount = fields.Float(compute='_compute_allowed_amount', string='Allowed Amount', digits=0, store=False)
    commitments = fields.Float(compute='_compute_commitments', string='Commitments', digits=0, store=False)
    dept_id = fields.Many2one('hr.department', 'Department',related='general_budget_id.department_id', store=True, readonly=False, copy=False)
    
    practical_amount = fields.Float(compute='_compute_practical_amount', string='Practical Amount', digits=0, store=False)
    theoritical_amount = fields.Float(compute='_compute_theoritical_amount', string='Theoretical Amount', digits=0, store=False)
    percentage = fields.Float(compute='_compute_percentage', string='Achievement', store=False)
    '''
    dept_id = fields.Many2one(
        comodel_name='account.budget.post')
    department = fields.Many2one(
        comodel_name='hr.department',
        related = 'dept_id.department_id',
        string='Department')
    '''
    @api.multi
    def _compute_theoritical_amount(self):
        today = fields.Datetime.now()
        for line in self:
            # Used for the report

            if self.env.context.get('wizard_date_from') and self.env.context.get('wizard_date_to'):
                date_from = fields.Datetime.from_string(self.env.context.get('wizard_date_from'))
                date_to = fields.Datetime.from_string(self.env.context.get('wizard_date_to'))
                if date_from < fields.Datetime.from_string(line.date_from):
                    date_from = fields.Datetime.from_string(line.date_from)
                elif date_from > fields.Datetime.from_string(line.date_to):
                    date_from = False

                if date_to > fields.Datetime.from_string(line.date_to):
                    date_to = fields.Datetime.from_string(line.date_to)
                elif date_to < fields.Datetime.from_string(line.date_from):
                    date_to = False

                theo_amt = 0.00
                if date_from and date_to:
                    line_timedelta = fields.Datetime.from_string(line.date_to) - fields.Datetime.from_string(line.date_from)
                    elapsed_timedelta = date_to - date_from
                    if elapsed_timedelta.days > 0:
                        theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
            else:
                if line.paid_date:
                    if fields.Datetime.from_string(line.date_to) <= fields.Datetime.from_string(line.paid_date):
                        theo_amt = 0.00
                    else:
                        theo_amt = line.planned_amount
                else:
                    line_timedelta = fields.Datetime.from_string(line.date_to) - fields.Datetime.from_string(line.date_from)
                    elapsed_timedelta = fields.Datetime.from_string(today) - (fields.Datetime.from_string(line.date_from))

                    if elapsed_timedelta.days < 0:
                        # If the budget line has not started yet, theoretical amount should be zero
                        theo_amt = 0.00
                    
                    elif line_timedelta.days > 0 and fields.Datetime.from_string(today) < fields.Datetime.from_string(line.date_to):
                        month_dif =int(str(fields.Datetime.from_string(today))[5:7]) - int(str(line.date_from)[5:7]) + 1
#                         interval = int(str(line.date_to)[5:7]) - int(str(line.date_from)[5:7]) + 1
                        interval = 12
                        theo_amt =  (line.planned_amount/interval) * month_dif
                    else:
                        theo_amt = line.planned_amount

            line.theoritical_amount = theo_amt
    
    @api.multi
    def _compute_allowed_amount(self):
        for line in self:
            line.allowed_amount = line.theoritical_amount + float((line.practical_amount or 0.0)) + float((line.commitments or 0.0))
    
    
    @api.multi
    def _compute_commitments(self):
        for line in self:
            result = 0.0
            acc_ids = line.general_budget_id.account_ids.ids
            date_to = self.env.context.get('wizard_date_to') or line.date_to
            date_from = self.env.context.get('wizard_date_from') or line.date_from
            if line.analytic_account_id.id:
                self.env.cr.execute("""
                    SELECT sum(price_total) 
                    from purchase_order_line 
                    WHERE account_analytic_id=%s
                    AND account_id=ANY(%s)
                    AND order_id in (SELECT id FROM purchase_order WHERE state in ('done','purchase') 
                    and invoice_status != 'invoiced'
                    and date_order between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd'))""",
                        (line.analytic_account_id.id, acc_ids, date_from, date_to,))
                result = self.env.cr.fetchone()[0] or 0.0
                
                self.env.cr.execute("""
                    SELECT sum(total_amount) 
                    from hr_expense 
                    WHERE analytic_account_id=%s
                    AND account_id=ANY(%s)
                    AND sheet_id in (SELECT id FROM hr_expense_sheet WHERE state = 'approve') 
                    and date between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')""",
                        (line.analytic_account_id.id, acc_ids, date_from, date_to,))
                result2 = self.env.cr.fetchone()[0] or 0.0
                
            line.commitments = -(result+result2)


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
#         if self.partner_id.vendor_registration == False:
#             raise UserError(_('Cant Confirm purchase order for an Unknown Vendor -- Request Vendor Registration.'))
    
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
            #raise ValidationError(_('Only your line manager can approve your leave request.'))
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
        ('to approve', 'To Approve'),
        ('submit', ' Line Manager Approval'),
        ('management', 'Management Approval'),
        ('legal', 'Awaiting Legal Review'),
        ('legal_reviewed', 'Reviewed'),
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
        #else:
         #   for user in group_id.users:
          #      user_ids.append(user.id)
           #     partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "RFQ '{}' needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
        return {}
    
    '''
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        self.request_date = date.today()
        partner_ids = [self.employee_id.user_id.partner_id.id]
        manager_id = self.employee_id.parent_id.user_id.partner_id.id
        partner_ids.append(manager_id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "RFQ '{}' needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=[manager_id])
        return False
    '''
                    
    @api.multi
    def action_line_manager_approval(self):
        self.write({'state':'to approve'})
        #self.manager_confirm()
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
                order.write({'state': 'to approve'})
            else:
                order.write({'state': 'to approve'})
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
    
    '''
    @api.multi
    def copy(self, default=None):
        new_po = super(PurchaseOrder, self).copy(default=default)
        for line in new_po.order_line:
            seller = line.product_id._select_seller(
                partner_id=line.partner_id, quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order[:10], uom_id=line.product_uom)
            line.date_planned = line._get_date_planned(seller)
            line.write({'need_override': False})
            line.write({'override_budget': False})
        return new_po
    '''
    
class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ['purchase.order.line']
    
    def _default_analytic(self):
        return self.env['account.analytic.account'].search([('name','=','sunray')])
    
    def _default_account(self):
        return self.product_id.property_account_expense_id
#     
#     @api.multi
#     @api.onchange('type')
#     def type_change(self):
#         self.product_id = False
    
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

class PurchaseRequisition(models.Model):
    _name = "purchase.requisition"
    _description = "Procurement Request"
    _inherit = ['purchase.requisition']
    
    @api.multi
    def _check_line_manager(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if current_employee == self.employee_id:
            return True
#             raise UserError(_('You are not allowed to approve your own request.'))
    
    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1)
    
    @api.depends('state')
    def _set_state(self):
        self.state_blanket_order = self.state
    
    state = fields.Selection(PURCHASE_REQUISITION_STATES,
                              'Status', track_visibility='onchange', required=True,
                              copy=False, default='draft')
    state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')
    
    #stock_source = fields.Char(string='Source document')
    store_request_id = fields.Many2one('stock.picking','Store Request', readonly=True, track_visibility='onchange')
    
    employee_id = fields.Many2one('hr.employee', 'Employee',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, default=_default_employee)
    
    request_date = fields.Date(string='Request Date', readonly=True, track_visibility='onchange', default=date.today())
    department_name = fields.Char(string="Employee Department", related="employee_id.department_id.name", readonly=True)
    
    approval_date = fields.Date(string='Manager Approval Date', readonly=True, track_visibility='onchange')
    manager_approval = fields.Many2one('res.users','Manager Approval Name', readonly=True, track_visibility='onchange')
    manager_position = fields.Char('Manager Position', readonly=True, track_visibility='onchange')
    
    po_approval_date = fields.Date(string='Authorization Date', readonly=True, track_visibility='onchange')
    po_manager_approval = fields.Many2one('res.users','Manager Authorization Name', readonly=True, track_visibility='onchange')
    po_manager_position = fields.Char('Manager Authorization Position', readonly=True, track_visibility='onchange')
    
    submitted = fields.Boolean(string='Submitted')
    
    line_manager_approval_date = fields.Date(string='Line-Manager Approval Date', readonly=True, track_visibility='onchange')
    line_manager_approval = fields.Many2one('res.users','Line-Manager Approval Name', readonly=True, track_visibility='onchange')
    
    total_cost = fields.Float(string='Total Cost', compute='_total_cost', track_visibility='onchange', readonly=True)
    
    type_of_request = fields.Selection([
        ('bid', 'Bid'),
        ('contract', 'Contract'),
        ('urgent', 'Urgent'),
        ('single_source', 'Single Source')], string='Type of Request',
        copy=False, default='bid', track_visibility='onchange')
    
    justification = fields.Char('Justification', readonly=False, track_visibility='onchange')
        
    @api.multi
    @api.depends('line_ids.price_subtotal')
    def _total_cost(self):
        for a in self:
            for line in a.line_ids:
                a.total_cost += line.price_subtotal
    
    @api.multi
    def button_submit_purchase_agreement(self):
        self.submitted = True
        self.write({'state':'submit'})
        #group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_hr_line_manager')
        #user_ids = []
        #partner_ids = []
        #partner_ids.append(self.employee_id.parent_id.user_id.partner_id.id)
        #for user in group_id.users:
        #    user_ids.append(user.id)
        #    partner_ids.append(self.employee_id.parent_id.user_id.partner_id.id)
        user_ids = []
        partner_ids = []
        if self.employee_id.parent_id.user_id:
            partner_ids.append(self.employee_id.parent_id.user_id.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Procurement Request '{}' needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
    
    @api.multi
    def action_line_manager_approval(self):
        self._check_line_manager()
        self.write({'state':'approve'})
        #self.manager_confirm()
        self.line_manager_approval_date = date.today()
        self.line_manager_approval = self._uid
#         if self.total_cost < 18150000.00:
        self.check_manager_approval_one()
#         else:
#             if self.total_cost > 18150000.00:
#                 self.check_manager_approval_two()
    
    @api.multi
    def action_in_progress(self):
        res = super(PurchaseRequisition, self).action_in_progress()
        self._check_line_manager()
        self.approval_date = date.today()
        self.manager_approval = self._uid
        return res
    
    @api.multi
    def action_open(self):
        self.write({'state': 'open'})
        self.po_approval_date = date.today()
        self.po_manager_approval = self._uid
        group_id = self.env['ir.model.data'].xmlid_to_object('purchase.group_purchase_manager')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Purchase Agreement {} has been confirmed & approved".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
    
    
    @api.depends('total_price')
    def check_manager_approval_one(self):
        if self.total_cost < 18150000.00:
            self.need_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_below_1st_authorization')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Procurement Request {} needs your approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_approval = False
            
    @api.depends('total_price')
    def check_manager_approval_two(self):
        if self.total_cost > 18150000.00:
            self.need_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_above_1st_authorization')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Purchase Agreement {} needs your approval, Above Quota".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_approval = False
    
    
class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _inherit = ['purchase.requisition.line']
    
    @api.onchange('product_id')
    def _onchange_partner_id(self):
        self.description = self.product_id.display_name
        self.price_unit = self.product_id.standard_price
        return {}
    
    price_unit = fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'))
    
    project_id = fields.Many2one(comodel_name='project.project', string='Site Location')
    
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=False)
    description = fields.Char(string='Description', required=True)
    
    price_subtotal = fields.Float(string="Price Subtotal", compute="_compute_subtotal", readonly=True)
    
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True)
    
    @api.one
    @api.depends('product_qty', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            self.price_subtotal = line.price_unit * self.product_qty
    
    @api.multi
    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        self.ensure_one()
        requisition = self.requisition_id
        if requisition.schedule_date:
            date_planned = datetime.datetime.combine(requisition.schedule_date, time.min)
        else:
            date_planned = datetime.datetime.now()
        if not self.product_id:
            raise UserError(_('Product(s) Must be created before becoming an RFQ'))
        return {
            #'name': name,
            'product_id': self.product_id.id,
            'name': self.description,
            'product_uom': self.product_id.uom_po_id.id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, taxes_ids)],
            'date_planned': date_planned,
            'account_analytic_id': self.account_analytic_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'move_dest_ids': self.move_dest_id and [(4, self.move_dest_id.id)] or []
        }
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    product_expiration_date = fields.Date(string='Product Expiration Date', track_visibility='onchange')
    
    @api.multi
    def send_expired_product_mail(self):
        test = False
        product = self.env['product.template'].search([])
        
        for self in product:
            if self.product_expiration_date:
                test = datetime.datetime.strptime(str(self.product_expiration_date), "%Y-%m-%d")
                
                birthday_day = test.day
                birthday_month = test.month
                
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                test_today = datetime.datetime.today().strptime(today, "%Y-%m-%d")
                birthday_day_today = test_today.day
                birthday_month_today = test_today.month
                
                if birthday_month == birthday_month_today:
                    if birthday_day == birthday_day_today:
                        config = self.env['mail.template'].sudo().search([('name','=','Birthday Reminder')], limit=1)
                        mail_obj = self.env['mail.mail']
                        if config:
                            values = config.generate_email(self.id)
                            mail = mail_obj.create(values)
                            if mail:
                                mail.send()
                            return True
        return
    
    @api.multi
    def send_product_expiration_mail(self):

        product = self.env['product.template'].search([])
        
        current_dates = False
        
        for self in product:
            if self.product_expiration_date:
                
                current_dates = datetime.datetime.strptime(str(self.product_expiration_date), "%Y-%m-%d")
                current_datesz = current_dates - relativedelta(days=7)
                
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
                            config = self.env['mail.template'].sudo().search([('name','=','Confirmation')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
                                return True
        return

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('manager_approval', 'Management Approval'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='draft')
    
    need_management_approval = fields.Boolean('Needs Management Approval', track_visibility="onchange", copy=False, default=False)
    
#     def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
#         location_id = order.shop_id.warehouse_id.lot_stock_id.id
#         output_id = order.shop_id.warehouse_id.lot_output_id.id
#         return {
#             'name': line.name,
#             'picking_id': picking_id,
#             'product_id': line.product_id.id,
#             'date': date_planned,
#             'date_expected': date_planned,
#             'product_qty': line.product_uom_qty,
#             'product_uom': line.product_uom.id,
#             'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
#             'product_uos': (line.product_uos and line.product_uos.id)\
#                     or line.product_uom.id,
#             'product_packaging': line.product_packaging.id,
#             'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
#             'location_id': location_id,
#             'location_dest_id': output_id,
#             'sale_line_id': line.id,
#             'tracking_id': False,
#             'state': 'draft',
#             #'state': 'waiting',
#             'company_id': order.company_id.id,
#             'price_unit': line.product_id.standard_price or 0.0
#         }
# 
#     def _prepare_order_picking(self, cr, uid, order, context=None):
#         pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
#         return {
#             'name': pick_name,
#             'origin': order.name,
#             'date': self.date_to_datetime(cr, uid, order.date_order, context),
#             'type': 'out',
#             'state': 'auto',
#             'move_type': order.picking_policy,
#             'sale_id': order.id,
#             'partner_id': order.partner_shipping_id.id,
#             'note': order.note,
#             'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
#             'company_id': order.company_id.id,
#         }
#     
#     def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
#         """Create the required procurements to supply sales order lines, also connecting
#         the procurements to appropriate stock moves in order to bring the goods to the
#         sales order's requested location.
# 
#         If ``picking_id`` is provided, the stock moves will be added to it, otherwise
#         a standard outgoing picking will be created to wrap the stock moves, as returned
#         by :meth:`~._prepare_order_picking`.
# 
#         Modules that wish to customize the procurements or partition the stock moves over
#         multiple stock pickings may override this method and call ``super()`` with
#         different subsets of ``order_lines`` and/or preset ``picking_id`` values.
# 
#         :param browse_record order: sales order to which the order lines belong
#         :param list(browse_record) order_lines: sales order line records to procure
#         :param int picking_id: optional ID of a stock picking to which the created stock moves
#                                will be added. A new picking will be created if ommitted.
#         :return: True
#         """
#         move_obj = self.pool.get('stock.move')
#         picking_obj = self.pool.get('stock.picking')
#         procurement_obj = self.pool.get('procurement.order')
#         proc_ids = []
# 
#         for line in order_lines:
#             if line.state == 'done':
#                 continue
# 
#             date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)
# 
#             if line.product_id:
#                 if line.product_id.type in ('product', 'consu'):
#                     if not picking_id:
#                         picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
#                     move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context))
#                 else:
#                     # a service has no stock move
#                     move_id = False
# 
#                 proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context))
#                 proc_ids.append(proc_id)
#                 line.write({'procurement_id': proc_id})
#                 self.ship_recreate(cr, uid, order, line, move_id, proc_id)
# 
#         wf_service = netsvc.LocalService("workflow")
#         if picking_id:
#             wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
#         for proc_id in proc_ids:
#             wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)
# 
#         val = {}
#         if order.state == 'shipping_except':
#             val['state'] = 'progress'
#             val['shipped'] = False
# 
#             if (order.order_policy == 'manual'):
#                 for line in order.order_line:
#                     if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
#                         val['state'] = 'manual'
#                         break
#         order.write(val)
#         return True
    
    @api.multi
    def action_cancel(self):
        sub = self.env['sale.subscription'].search([('stage_id.name','=','In Progress'), ('partner_id', '=', self.partner_id.id), ('sale_order_id', '=', self.id)])
        if sub:
            sub.write({'stage_id': 4})
        return self.write({'state': 'cancel'})
    
    @api.multi
    def _check_customer_registration(self):
        if self.partner_id.customer_registration == False:
            raise UserError(_('Cant Confirm sale order for an unregistered customer -- Request Customer Registration.'))

    
    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        #self._check_approval()
        
        self._check_customer_registration()
        return res
    
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
            subject = "Sales Order {} needs management approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return self.state
            #raise ValidationError(_('Only your line manager can approve your leave request.'))
        else:
            self.need_approval = False
            
    
    def _prepare_subscription_data(self, template):
        """Prepare a dictionnary of values to create a subscription from a template."""
        self.ensure_one()
        values = {
            'name': template.name,
            'template_id': template.id,
            'partner_id': self.partner_invoice_id.id,
            'sale_order_id': self.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'date_start': fields.Date.today(),
            'description': self.note or template.description,
            'pricelist_id': self.pricelist_id.id,
            'company_id': self.company_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'payment_token_id': self.transaction_ids.get_last_transaction().payment_token_id.id if template.payment_mode in ['validate_send_payment', 'success_payment'] else False
        }
        default_stage = self.env['sale.subscription.stage'].search([('in_progress', '=', True)], limit=1)
        if default_stage:
            values['stage_id'] = default_stage.id
        # compute the next date
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[template.recurring_rule_type]: template.recurring_interval})
        recurring_next_date = today + invoicing_period
        values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        return values
    

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _description = 'Sales Order Line'
    _inherit = ['sale.order.line']
    
    @api.onchange('site_code_id')
    def _onchange_partner_id(self):
        self.analytic_account_id = self.site_code_id.project_id.analytic_account_id
        return {}
    
    type = fields.Selection([('sale', 'Sale'), ('lease', 'Lease')], string='Type', required=True, default='sale')
    project_id = fields.Many2one(comodel_name="project.project", string="Site Location")
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False)
    
    def _prepare_subscription_line_data(self):
        """Prepare a dictionnary of values to add lines to a subscription."""
        values = list()
        for line in self:
            values.append((0, False, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'uom_id': line.product_uom.id,
                'price_unit': line.price_unit,
                'site_code_id': line.site_code_id.id,
                #'analytic_account_id': line.analytic_account_id,
                'discount': line.discount if line.order_id.subscription_management != 'upsell' else False,
            }))
        return values
    
    @api.multi
    def _timesheet_create_project(self):
        """ Generate project for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return task: record of the created task
        """
        self.ensure_one()
        account = self.order_id.analytic_account_id
        if not account:
            self.order_id._create_analytic_account(prefix=self.product_id.default_code or None)
            account = self.order_id.analytic_account_id

        # create the project or duplicate one
        values = {
            'name': '%s - %s' % (self.order_id.client_order_ref, self.order_id.name) if self.order_id.client_order_ref else self.site_code_id.name + " " + "-" + " " + self.order_id.partner_id.name + " - " + self.site_code_id.site_area,
            'allow_timesheets': True,
            'analytic_account_id': account.id,
            'partner_id': self.order_id.partner_id.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'site_code_id': self.site_code_id.id,
            'site_area': self.site_code_id.site_area,
            'site_location_id': self.site_code_id.state_id.id,
            'active': True,
        }
        if self.product_id.project_template_id:
            values['name'] = "%s - %s" % (values['name'], self.product_id.project_template_id.name)
            project = self.product_id.project_template_id.copy(values)
            project.tasks.write({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id,
                'email_from': self.order_id.partner_id.email,
            })
            # duplicating a project doesn't set the SO on sub-tasks
            project.tasks.filtered(lambda task: task.parent_id != False).write({
                'sale_line_id': self.id,
            })
        else:
            project = self.env['project.project'].create(values)
        # link project as generated by current so line
        self.write({'project_id': project.id})
        return project

class SaleSubscription(models.Model):
    _inherit = "sale.subscription"
    
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')

class SaleSubscriptionLine(models.Model):
    _inherit = "sale.subscription.line"
    
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    
    account_analytic_id = fields.Many2one(comodel_name='account.analytic.account', string="Analytic Account", copy=False)
    
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
    
    '''
    @api.multi
    def _check_site_code(self):
        site_code = self.env['site.code'].search([('name', '=', self.name)], limit=1)
        if site_code.name == self.name:
            raise UserError(_('Site Code Already Exists'))
    '''
    
    location_id = fields.Many2one('stock.location', string='Location', ondelete="restrict", required=True)

    state_id = fields.Many2one(comodel_name='res.country.state', string='Site location (State)', required=True, track_visibility='onchange')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', required=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', required=False)
#     name = fields.Char('Code', readonly=False, track_visibility='onchange')
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
        #existing_site = self.env['site.code'].search([('state_id','=',vals['state_id']), ('partner_id', '=',vals['partner_id'])], limit=1)
        #if existing_site:
        #    self.num = existing_site.num + 1
        #else:
        #    self.num = 1
        if client.parent_account_number:
            code = client.parent_account_number + "_" + site.code
        else:
            raise UserError(_('There is no customer code for the customer'))
        
        no = self.env['ir.sequence'].next_by_code('project.site.code')
        #no = self.num
        site_code = code + "_" +  str(no)
        print(site_code)
        #vals['name'] = site_code
        vals['usage'] = 'customer'
        #self._check_site_code()
#         res_model, res_id = self.env['ir.model.data'].get_object_reference('stock','stock_location_locations_partner')
#         product = self.env[res_model].browse(res_id) 
        return super(SiteCode, self).create(vals)
    
    #@api.onchange('name')
    #def write(self, vals):
        #site = self.env['site.code'].search([('name','=',vals['name'])])
        #if site:
            #raise UserError(_('Site Code Must Unique!'))
        #return super(SiteCode, self).write(vals)
    
    '''
    @api.multi
    def action_generate(self):
        if self.partner_id and self.location_id:
            code = self.partner_id.parent_account_number + "_" +  self.location_id.code
            no = self.env['ir.sequence'].next_by_code('project.site.code')
            site_code = code + "_" +  str(no)
            self.name = site_code
    '''
    
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
    
    #@api.model
    #def create(self, vals):
     #   site = self.env['site.location'].search([('id','=',vals['site_location_id'])])
      #  client = self.env['res.partner'].search([('id','=',vals['partner_id'])])
       # code = site.code + client.client_code
       # 
        #no = self.env['ir.sequence'].next_by_code('project.site.code')
        #site_code = code + str(no)
        #vals['default_site_code'] = site_code
        #return super(Project, self).create(vals)
    
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
    
class Picking(models.Model):
    _name = "stock.picking"
    _inherit = 'stock.picking'
    
    @api.one
    @api.depends('site_code_id','site_code_id.project_id')
    def _get_analytic_account(self):
        if self.site_code_id.project_id.analytic_account_id:
            self.analytic_account_id = self.site_code_id.project_id.analytic_account_id.id
    
    analytic_account_id = fields.Many2one(
        string='Analytic Account',
        comodel_name='account.analytic.account', compute='_get_analytic_account', store=True 
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('submit', 'Submitted'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
             " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
             " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")
    
    inventory_validation = fields.Boolean(string='inventory validation')
    
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_hr_line_manager')
        user_ids = []
        partner_ids = []
        if self.employee_id.parent_id.user_id:
            partner_ids.append(self.employee_id.parent_id.user_id.partner_id.id)
        else:
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Store request {} needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
        return {}
    
    @api.multi
    def receipt_validation_inventory(self):
        if self.picking_type_id.name == "Receipts":
            self.inventory_validation = True
            group_id = self.env['ir.model.data'].xmlid_to_object('purchase.group_purchase_manager')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Stock Receipt {} has been validated by Inventory, awaiting Procurement validation".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        return True
    
    @api.multi
    def button_validate(self):
        res = super(Picking, self).button_validate()
        if self.picking_type_id.name == "Receipts" and self.inventory_validation == False:
            self.receipt_validation_inventory()
        else:
            if self.user_has_groups('purchase.group_purchase_manager'):
                return res
        
    
    @api.multi
    def action_confirm(self):
        res = super(Picking, self).action_confirm()
        if self.picking_type_id.name == 'Staff Store Requests':
            self.button_approve_srt()
            group_id = self.env['ir.model.data'].xmlid_to_object('stock.group_stock_manager')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Store request {} has been authorized".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            subject = "Request {} has been approved".format(self.name)
            partner_ids = []
            for partner in self.message_partner_ids:
                partner_ids.append(partner.id)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return res
    
    @api.multi
    def action_line_manager_approval(self):
        self.write({'state':'approve'})
        self.manager_confirm()
        self.action_confirm()
        self.notify_store()
        #if self.total_cost < 18150000.00:
        #    self.check_manager_approval_one()
        #else:
        #    if self.total_cost > 18150000.00:
        #        self.check_manager_approval_two()
        
    @api.multi
    def notify_store(self):
        group_id = self.env['ir.model.data'].xmlid_to_object('stock.group_stock_manager')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Request {} has been approved".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def manager_confirm(self):
        for order in self:
            order.write({'man_confirm': True})
        return True
    
    def _default_owner(self):
        return self.env.context.get('default_employee_id') or self.env['res.users'].browse(self.env.uid).partner_id
    
    def _default_employee(self):
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])
    
    @api.onchange('site_code_id')
    def _onchange_site_id(self):
        self.partner_id = self.site_code_id.partner_id
        self.location_dest_id = self.site_code_id.location_id
    
    owner_id = fields.Many2one('res.partner', 'Owner',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, default=_default_owner,
        help="Default Owner")
    
    employee_id = fields.Many2one('hr.employee', 'Employee',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, default=_default_employee,
        help="Default Owner")
    
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    
    man_confirm = fields.Boolean('Manager Confirmation', track_visibility='onchange')
    #net_lot_id = fields.Many2one(string="Serial Number", related="move_line_ids.lot_id", readonly=True)
    internal_transfer = fields.Boolean('Internal Transfer?', track_visibility='onchange')
    client_id = fields.Many2one('res.partner', string='Client', index=True, ondelete='cascade', required=False)
    need_approval = fields.Boolean ('Need Approval', track_visibility="onchange", copy=False)
    #rejection_reason = fields.Many2one('stock.rejection.reason', string='Rejection Reason', index=True, track_visibility='onchange')
    
    project_id = fields.Many2one('project.project', string='Project', index=True, ondelete='cascade', required=False)
    
    total_price = fields.Float(string='Total', compute='_total_price', readonly=True, store=True)
    
    total_cost = fields.Float(string='Total Cost', compute='_total_cost', track_visibility='onchange', readonly=True)
    send_receipt_mail = fields.Boolean(string='receipt mail')
    
    picking_type_id_name = fields.Char(string='Picking Type Name', related='picking_type_id.name')
    picking_type_id_code = fields.Selection([('incoming', 'Vendors'), ('outgoing', 'Customers'), ('internal', 'Internal')], string='Picking Type Code', related='picking_type_id.code')
    
    order_no = fields.Char(string='Order No/Model')
    ship_status = fields.Char(string='Shipment Status')
    bu = fields.Char(string='BU')
    type_of_cargo = fields.Char(string='Type of Cargo')
    supplier = fields.Char(string='Supplier')
    pfi_no_bl = fields.Char(string='PFI No/BL')
    incoterms = fields.Char(string='Incoterms')
    incoterms_location = fields.Char(string='Incoterm Location')
    country_of_supplier_id = fields.Many2one(comodel_name='res.country', string='Country of Supply')
    logistics_provider = fields.Char(string='Logistics Provider (3PL Co)')
    
    mode_of_transport = fields.Char(string='Mode of Transport')
    date_of_equipment = fields.Date(string='Date of Equipment needed')
    target_shipment_date = fields.Date(string='Target Shipment Date')
    actual_shipment_date = fields.Char(string='Actual Shipment Date')
    eta = fields.Char(string='ETA')
    ata = fields.Char(string='ATA')
    arrival_at_warehouse = fields.Char(string='Arrival at warehouse')
    
    pfi = fields.Char(string='PFI')
    product_certificate = fields.Char(string='Product Certificate')
    insurance = fields.Char(string='Insurance')
    form_m = fields.Char(string='Fom M')
    
    bill_of_landing = fields.Char(string='Bill of Lading')
    ccvo = fields.Char(string='Commercial invoice')
    packing_list = fields.Char(string='Packing list')
    soncap = fields.Char(string='SONCAP')
    paar = fields.Char(string='PAAR')
    
    
    @api.multi
    @api.depends('move_ids_without_package.product_uom_qty')
    def _total_cost(self):
        for a in self:
            for line in a.move_ids_without_package:
                a.total_cost += line.price_cost * line.product_uom_qty
    
    @api.depends('total_price')
    def check_manager_approval_one(self):
        if self.total_price < 18150000.00:
            self.need_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_below_1st_authorization')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Store request {} needs your approval, Below Quota".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_approval = False
            
    @api.depends('total_price')
    def check_manager_approval_two(self):
        if self.total_price > 18150000.00:
            self.need_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_above_1st_authorization')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Store request {} needs your approval, Above Quota".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_approval = False
    
    '''
    @api.depends('total_price')
    def check_approval(self):
        if self.total_price > 1800000:
            self.need_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('stock.group_stock_manager')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Store request {} needs approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        else:
            self.need_approval = False
    '''
                
    @api.multi
    def button_approve_srt(self):
        self.need_approval = False
        return {}
    
    @api.multi
    def button_reset(self):
        self.mapped('move_lines')._action_cancel()
        self.write({'state': 'draft'})
        return {}
    
    @api.model
    def create(self, vals):
        a = super(Picking, self).create(vals)
        a.send_store_request_mail()
        return a
        return super(Picking, self).create(vals)
    
    @api.multi
    def send_store_request_mail(self):
        if self.picking_type_id.name == "Staff Store Requests" and self.state in ['draft','waiting','confirmed']:
            group_id = self.env['ir.model.data'].xmlid_to_object('stock.group_stock_manager')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "A new store request {} has been made".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return False
        return True
    
    @api.multi
    def send_store_request_done_mail(self):
        if self.state in ['done']:
            subject = "Store request {} has been approved and validated".format(self.name)
            partner_ids = []
            for partner in self.sheet_id.message_partner_ids:
                partner_ids.append(partner.id)
            self.sheet_id.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    
    @api.multi
    def send_receipt_mail(self):
        if self.picking_type_id.name == "Receipts":
            self.send_receipt_mail = True
            config = self.env['mail.template'].sudo().search([('name','=','recieved')], limit=1)
            mail_obj = self.env['mail.mail']
            if config:
                values = config.generate_email(self.id)
                mail = mail_obj.create(values)
                if mail:
                    mail.send()
            subject = "Receipt mail has been sent to this supplier".format(self.name)
            partner_ids = []
            for partner in self.message_partner_ids:
                partner_ids.append(partner.id)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    def create_purchase_order(self):
        """
        Method to open create purchase order form
        """

        partner_id = self.client_id
        client_id = self.client_id
        #store_request_id = self.id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('purchase', 'purchase_order_form')
        view_id = view_ref[1] if view_ref else False
        
        #purchase_line_obj = self.env['purchase.order.line']
        for subscription in self:
            order_lines = []
            for line in subscription.move_lines:
                order_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'account_id': line.account_id.id,
                    'product_qty': line.product_uom_qty,
                    'date_planned': date.today(),
                    'price_unit': line.product_id.standard_price,
                }))
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Purchase Order'),
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_client_id': client_id.id, 'default_stock_source': self.name, 'default_store_request_id': self.id, 'default_order_line': order_lines}
        }
        
        return res
    
    
    @api.multi
    def create_purchase_agreement(self):
        """
        Method to open create purchase agreement form
        """

        partner_id = self.client_id
        client_id = self.client_id
        #store_request_id = self.id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('purchase_requisition', 'view_purchase_requisition_form')
        view_id = view_ref[1] if view_ref else False
        
        #purchase_line_obj = self.env['purchase.order.line']
        for subscription in self:
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
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Purchase Agreement'),
            'res_model': 'purchase.requisition',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_type_id': 2, 'default_origin': self.name, 'default_store_request_id': self.id, 'default_line_ids': order_lines}
        }
        
        return res
    
    @api.one
    @api.depends('move_lines.price_unit')
    def _total_price(self):
        total_unit = 0.0
        for line in self.move_lines:
            self.total_price += line.price_subtotal
    
    @api.multi
    def create_delivery_list(self):
        """
        Method to open create packing list form
        """

        partner_id = self.partner_id
        sale_id = self.sale_id.id
        
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('stock', 'view_picking_form')
        view_id = view_ref[1] if view_ref else False
        
        
        #purchase_line_obj = self.env['purchase.order.line']
        for subscription in self:
            order_lines = []
            for line in subscription.move_ids_without_package:
                order_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'state': "assigned",
                    'product_uom': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'reserved_availability': line.reserved_availability,
                    'product_uom_qty': line.product_uom_qty,
                    'additional': True,
                    'date_expected': date.today(),
                    'price_cost': line.product_id.standard_price,
                }))
        
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Packing List'),
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_origin': self.name, 'default_partner_id': partner_id.id, 'default_sale_id': sale_id, "default_is_locked":True, "default_state":"assigned",  "default_picking_type_id":22, 'default_move_ids_without_package': order_lines}
        }
        
        return res
    
    @api.multi
    def create_parking_list(self):
        """
        Method to open create delivery list form
        """

        partner_id = self.partner_id
        #client_id = self.request_client_id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('stock', 'view_picking_form')
        view_id = view_ref[1] if view_ref else False
        
        
        #purchase_line_obj = self.env['purchase.order.line']
        for subscription in self:
            order_lines = []
            for line in subscription.move_ids_without_package:
                order_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'state': "assigned",
                    'product_uom': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'reserved_availability': line.reserved_availability,
                    'product_uom_qty': line.product_uom_qty,
                    'additional': True,
                    'date_expected': date.today(),
                    'price_cost': line.product_id.standard_price,
                }))
        
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Packing List'),
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_origin': self.name, 'default_partner_id': partner_id.id, "default_is_locked":False, "default_state":"assigned", "default_picking_type_id":24, 'default_move_ids_without_package': order_lines}
        }
        
        return res

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    
    department_id = fields.Many2one(comodel_name='hr.department', string='Department')
    
    '''
    @api.multi
    def name_get(self):
        if self.project_ids:
            res = []
            for project in self.project_ids:
                result = project.name
                if project.site_code_id.name:
                    result = str(project.site_code_id.name) + " " + "-" + " " + str(project.partner_id.name) + " - " + str(project.site_area)
                res.append((project.id, result))
            return res
    '''
    
class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['account.move', 'mail.thread', 'mail.activity.mixin']
    
class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    from_sale = fields.Boolean(string='Sale', compute='_check_sale_from', track_visibility="onchange", readonly=True)
    
    type_of_invoice = fields.Selection([
        ('regular', 'Regular'),
        ('additional_hours', 'Additional Hours')], string='Type of Invoice',
        default='regular', track_visibility='onchange')
    
    @api.multi
    def _check_analytic_account(self):
        for line in self.invoice_line_ids:
            if not line.display_type:
                if not line.account_analytic_id:
                    raise UserError(_('Please ensure analytic account has been set on all invoice lines'))
                
    
    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        self._check_analytic_account()
        return res
    
    @api.multi
    def update_vat(self):
        self.action_invoice_cancel()
        self.action_invoice_draft()
        for line in self.tax_line_ids:
            if line.account_id.id == 20951:
                line.account_id = 20949
    
    @api.multi
    def update_analytic_account(self):
        for line in self.invoice_line_ids:
            line.account_analytic_id = line.site_code_id.project_id.analytic_account_id
    
    @api.depends('origin')
    def _check_sale_from(self):
        if self.origin:
            if "SO0" in self.origin:
                self.from_sale = True
            
    def _default_employee(self):
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])
    
    @api.multi
    def _check_customer_registration(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if self.partner_id.customer_registration == False:
            raise UserError(_('Cant validate invoice for an unregistered customer -- Request Customer Registration.'))
        if not current_employee == 637:
            raise UserError(_('You are not allowed to approve your own request.'))
    
    employee_id = fields.Many2one('hr.employee', 'Employee',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, default=_default_employee)
        
        
class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    @api.onchange('site_code_id')
    def _onchange_site_id(self):
        self.account_analytic_id = self.site_code_id.project_id.analytic_account_id
        return {}
    
    from_sale = fields.Boolean(string='Sale', related='invoice_id.from_sale', track_visibility="onchange", readonly=True)
    
    rate_min = fields.Char(string='Rate/min')
    
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    
    #account_analytic_id = fields.Many2one('account.analytic.account',
        #string='Analytic Account', required=True)

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'
    
    asset_quantity = fields.Float(string='Quantity')
    asset_total = fields.Float(string='Total', compute='_compute_asset_total')
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    asset_partner_id = fields.Many2one(comodel_name="res.partner", string="Customer")
    
    type_of_close = fields.Selection([
        ('sold', 'Sold'),
        ('decommissioned', 'Decommissioned')], string='Type of Closure', track_visibility='onchange')
    
    date_of_decommissioned = fields.Date(string='Date of Decommission')
    
    @api.onchange('site_code_id')
    def _onchange_partner_id(self):
        self.asset_partner_id = self.site_code_id.partner_id
        return {}
    
    @api.depends('value', 'asset_quantity')
    def _compute_asset_total(self):
        self.asset_total = self.value * self.asset_quantity
    
    @api.multi
    def update_analytic_account(self):
        if not self.account_analytic_id:
            self.account_analytic_id = self.site_code_id.project_id.analytic_account_id
        if not self.asset_partner_id:
            self.asset_partner_id = self.site_code_id.partner_id
            
    @api.multi
    def _update_all_analytic_account(self):
        assets = self.env['account.asset.asset'].search([])
        for assets in assets:
            #self.update_analytic_account()
            if not assets.account_analytic_id:
                assets.account_analytic_id = assets.site_code_id.project_id.analytic_account_id
            if not assets.asset_partner_id:
                assets.asset_partner_id = self.site_code_id.partner_id
    
class StockMove(models.Model):
    _inherit = "stock.move"
    
    @api.one
    @api.depends('product_uom_qty', 'price_cost')
    def _compute_subtotal(self):
        for line in self:
            self.price_subtotal = self.product_uom_qty * line.price_cost
    
    def _default_cost(self):
        return self.product_id.standard_price
    
#     def _default_analytic(self):
#         return self.env['account.analytic.account'].search([('name','=','Sunray')])
    
    @api.multi
    @api.onchange('product_id')
    def product_change(self):
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        if self.location_dest_id.valuation_in_account_id:
            acc_dest = self.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts_data['stock_output'].id
        self.account_id = acc_dest

    @api.multi
    def _prepare_account_move_line(self, qty, cost,
                                   credit_account_id, debit_account_id):
        self.ensure_one()
        res = super(StockMove, self)._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id)
        # Add analytic account in debit line
        if not res:
            return res
        if not self.analytic_account_id and self.picking_id and self.picking_id.site_code_id:
            self.sudo().picking_id.site_code_id.create_project_from_site_code()

        for num in range(0, 2):
            if res[num][2]["account_id"] != self.product_id.\
                    categ_id.property_stock_valuation_account_id.id:
                res[num][2].update({
                    'analytic_account_id': self.analytic_account_id.id,
                })
        return res
    
    def create_account(self):
        self._account_entry_move()
        return True
        
    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        self.ensure_one()
        AccountMove = self.env['account.move']
        quantity = self.env.context.get('forced_quantity', self.product_qty)
        quantity = quantity if self._is_in() else -1 * quantity

        # Make an informative `ref` on the created account move to differentiate between classic
        # movements, vacuum and edition of past moves.
        ref = self.picking_id.name
        if self.env.context.get('force_valuation_amount'):
            if self.env.context.get('forced_quantity') == 0:
                ref = 'Revaluation of %s (negative inventory)' % ref
            elif self.env.context.get('forced_quantity') is not None:
                ref = 'Correction of %s (modification of past move)' % ref

        move_lines = self.with_context(forced_ref=ref)._prepare_account_move_line(quantity, abs(self.value), credit_account_id, debit_account_id)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': ref,
                'stock_move_id': self.id,
            })
#             new_account_move.post()
        
    @api.multi
    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        if self.location_id.valuation_out_account_id:
            acc_src = self.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts_data['stock_input'].id

        if self.account_id:
            acc_dest = self.account_id.id
        elif self.location_dest_id.valuation_in_account_id:
            acc_dest = self.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts_data['stock_output'].id

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation
    
#     @api.model
#     def _get_account_id(self):
#         accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
#         print(accounts_data) 
#         if self.location_dest_id.valuation_in_account_id:
#             acc_dest = self.location_dest_id.valuation_in_account_id.id
#         else:
#             acc_dest = accounts_data['stock_output'].id
#         return acc_dest
        
    
#     account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Acount', required=False, default=_default_analytic, track_visibility="always")
    analytic_account_id = fields.Many2one(
        related='picking_id.analytic_account_id', store=True)
    account_id = fields.Many2one('account.account', string='Account', index=True, ondelete='cascade')
    
    price_cost = fields.Float(string="Cost", related='product_id.standard_price')
    price_subtotal = fields.Float(string="Price Subtotal", compute="_compute_subtotal", readonly=True)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    analytic_account_id = fields.Many2one(
        related='move_id.analytic_account_id')

class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    total_bom_cost = fields.Float(string='Total Cost', compute='_compute_bom_total')
    
    @api.depends('bom_line_ids.subtotal_estimated_cost')
    def _compute_bom_total(self):
        for line in self.bom_line_ids:
            self.total_bom_cost += line.subtotal_estimated_cost
    
class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'    
    
    bom_unit_cost = fields.Float(string='Unit Cost', related='product_id.standard_price')
    subtotal_estimated_cost = fields.Float(string='Total Estimated Cost', compute='_compute_bom_subtotal_total')
    
    @api.depends('bom_unit_cost', 'product_qty')
    def _compute_bom_subtotal_total(self):
        for line in self:
            line.subtotal_estimated_cost = line.bom_unit_cost * line.product_qty
    
    
class MrpProduction(models.Model):
    _inherit = "mrp.production"    
    
    state = fields.Selection([
        ('unconfirmed', 'Unconfirmed'),
        ('confirmed', 'Confirmed'),
        ('planned', 'Planned'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State',
        copy=False, default='unconfirmed', track_visibility='onchange')
    
    def _default_partner(self):
        return self.project_id.partner_id.id
    
    project_id = fields.Many2one(comodel_name='project.project', string='Projects')
    
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', readonly=False, default=_default_partner)
    
    total_cost = fields.Float(string='Total Cost', compute='_total_cost', track_visibility='onchange', readonly=True)
    
    project_budget = fields.Float(string='Project Budget', related='project_id.project_budget', track_visibility='onchange', readonly=True)
    
    approved_mo = fields.Boolean ('Approved MO', track_visibility="onchange", readonly=True)
    
    @api.model
    def create(self, vals):
        result = super(MrpProduction, self).create(vals)
        result.mrp_created()
        return result
    
    @api.multi
    def mrp_created(self):
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_head_projects','project.group_project_manager')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Manufacturing Order {} has been created and needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_mrp_approved(self):
        self.write({'state': 'confirmed'})
        self.approved_mo = True
        subject = "Manufacturing Order {} has been approved".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.multi
    @api.depends('move_raw_ids.product_uom_qty')
    def _total_cost(self):
        for a in self:
            for line in a.move_raw_ids:
                a.total_cost += line.price_cost * line.product_uom_qty
                
    
    @api.multi
    def create_store_request(self):
        """
        Method to open create purchase order form
        """

        #partner_id = self.request_client_id
        #client_id = self.request_client_id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('sunray', 'sunray_stock_form_view')
        view_id = view_ref[1] if view_ref else False
        
        #purchase_line_obj = self.env['purchase.order.line']
        for subscription in self:
            order_lines = []
            for line in subscription.move_raw_ids:
                order_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'reserved_availability': line.reserved_availability,
                    'product_uom_qty': line.product_uom_qty,
                    'additional': True,
                    'date_expected': date.today(),
                    'price_cost': line.product_id.standard_price,
                }))
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Store Request'),
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_origin': self.name, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id, 'default_move_lines': order_lines}
        }
        
        return res
    
    
class Repair(models.Model):
    _inherit = 'repair.order'
    
    @api.multi
    def create_store_request(self):
        """
        Method to open create store request form
        """
             
        view_ref = self.env['ir.model.data'].get_object_reference('sunray', 'sunray_stock_form_view')
        view_id = view_ref[1] if view_ref else False
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Store Request'),
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_origin': self.name, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id}
        }
        
        return res
    
class RepairLine(models.Model):
    _inherit = 'repair.line'
        
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'
    
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    
    @api.multi
    def create_repair_request(self):
        """
        Method to open create repair order form
        """
                     
        view_ref = self.env['ir.model.data'].get_object_reference('repair', 'view_repair_order_form')
        view_id = view_ref[1] if view_ref else False
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Repair Order'),
            'res_model': 'repair.order',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            #'context': {'default_origin': self.name, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id, 'default_move_lines': order_lines}
        }
        
        return res
    
    @api.multi
    def create_store_request(self):
        """
        Method to open create store request form
        """
             
        view_ref = self.env['ir.model.data'].get_object_reference('sunray', 'sunray_stock_form_view')
        view_id = view_ref[1] if view_ref else False
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Store Request'),
            'res_model': 'stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_origin': self.name, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id}
        }
        
        return res

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    
    @api.multi
    def close_payslip_run(self):
        self.slip_ids.action_payslip_done()
        return self.write({'state': 'close'})

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    prorate_days = fields.Float(string='Proration Days', required=False, help="Proration Days")
    
    #@api.onchange('prorate_days')
    #def _check_proration(self):
     #   if self.prorate_days > 0:
      #      for line in self.line_ids:
       #         line.amount = line.amount*self.prorate_days/self.worked_days_line_ids.number_of_days
    
    @api.multi
    def action_payslip_done(self):
        self.compute_sheet()

        for slip in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move_dict = {
                #'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    debit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=False),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=True),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                })
                line_ids.append(adjust_credit)

            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date})
            #move.post()
        return self.write({'state': 'done'})





             
    