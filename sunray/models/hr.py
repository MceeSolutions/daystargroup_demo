from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero


class Employee(models.Model):
    _name = "hr.employee"
    _description = "Employee"
    _inherit = "hr.employee"
    
    deactivated = fields.Boolean(string='Deactivated')
    deactivation_date = fields.Date(string='Deactivation Date', readonly=True)
    pf_id = fields.Many2one('pen.type', string='Penson Fund Administrator', index=True)
    
    pension_institution = fields.Char(string="Pension Institution")
    pension_account_number = fields.Char(string="Pension Account Number")
    
    @api.multi
    def reminder_deactivate_employee_contract(self):
        group_id = self.env['ir.model.data'].xmlid_to_object('hr.group_hr_manager')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This is a reminder to deactivate any running contract for this employee".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
        return {}
    
    @api.multi
    def button_deactivate_employee(self):
        self.ensure_one()
        if self.active == True:
            config = self.env['mail.template'].sudo().search([('name','=','Employee Departure')], limit=1)
            mail_obj = self.env['mail.mail']
            if config:
                values = config.generate_email(self.id)
                mail = mail_obj.create(values)
                if mail:
                    mail.send()
            self.active = False
            self.deactivated = True
            self.deactivation_date = date.today()
            self.reminder_deactivate_employee_contract()
    
    
    @api.multi
    def send_birthday_mail(self):
        test = False
        employees = self.env['hr.employee'].search([])
        
        for self in employees:
            if self.active == True:
                if self.birthday:
                    test = datetime.datetime.strptime(str(self.birthday), "%Y-%m-%d")
                    
                    birthday_day = test.day
                    birthday_month = test.month
                    
                    today = datetime.datetime.now().strftime("%Y-%m-%d")
                    
                    test_today = datetime.datetime.today().strptime(today, "%Y-%m-%d")
                    birthday_day_today = test_today.day
                    birthday_month_today = test_today.month
                    
                    if birthday_month == birthday_month_today:
                        if birthday_day == birthday_day_today:
                            config = self.env['mail.template'].sudo().search([('name','=','Birthday Congratulations')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
                                return True
        return

class Department(models.Model):
    _inherit = "hr.department"
    
    department_code = fields.Char(string='Department Code')
    
    @api.model
    def create(self, vals):
        result = super(Department, self).create(vals)
        result.create_analytic_account()
        return result
    
    @api.multi
    def create_analytic_account(self):
        self.ensure_one()
        # create the department analytic account
        values = {
            'name': '%s' % (self.name),
            'department_id': self.id,
            'active': True,
        }
        department = self.env['account.analytic.account'].create(values)
        return department
    
class Job(models.Model):

    _name = "hr.job"
    _inherit = "hr.job"
    
    appliaction_deadline = fields.Date(string="Application Deadline")
    todays_date = fields.Date(string="Todays Date", default = date.today())
    
    @api.multi
    def check_deadline(self):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if self.appliaction_deadline == today:
            self.set_open()


class HolidaysRequest(models.Model):
    _name = "hr.leave"
    _inherit = "hr.leave"
    
    @api.model
    def create(self, vals):
        result = super(HolidaysRequest, self).create(vals)
        result.send_mail()
        return result
    
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help="The status is set to 'To Submit', when a leave request is created." +
        "\nThe status is 'To Approve', when leave request is confirmed by user." +
        "\nThe status is 'Refused', when leave request is refused by manager." +
        "\nThe status is 'Approved', when leave request is approved by manager.")
    
    @api.multi
    def _check_line_manager(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if current_employee == self.employee_id:
            raise UserError(_('Only your line manager can approve your leave request.'))
    
    @api.multi
    def send_mail(self):
        incomplete_propation_period = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state','=','open'), ('trial_date_end','>',date.today())], limit=1)
        
        unset_propation_period_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id), ('state','=','open')], limit=1)
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        current_dates = datetime.datetime.strptime(today, "%Y-%m-%d")
        
        contract_start_date = unset_propation_period_contract.date_start
        
        between_contracts = relativedelta(current_dates, contract_start_date)
        months_between_contracts = between_contracts.months
        
        if incomplete_propation_period:
            raise UserError(_("You currently can't apply for leave as your probation period isn't over"))
        elif months_between_contracts < 5:
            raise UserError(_("You currently can't apply for leave as your contract hasn't exhausted 5 months"))
        else:
            if self.state in ['confirm']:
                config = self.env['mail.template'].sudo().search([('name','=','Leave Approval Request Template')], limit=1)
                mail_obj = self.env['mail.mail']
                if config:
                    values = config.generate_email(self.id)
                    mail = mail_obj.create(values)
                    if mail:
                        mail.send()
                        
    @api.multi
    def send_manager_approved_mail(self):
        config = self.env['mail.template'].sudo().search([('name','=','Leave Manager Approval')], limit=1)
        mail_obj = self.env['mail.mail']
        if config:
            values = config.generate_email(self.id)
            mail = mail_obj.create(values)
            if mail:
                mail.send()
                
    @api.multi
    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))
        
        self._check_line_manager()
        
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.send_manager_approved_mail()
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True
    
    @api.multi
    def send_hr_approved_mail(self):
        config = self.env['mail.template'].sudo().search([('name','=','Leave HR Approval')], limit=1)
        mail_obj = self.env['mail.mail']
        if config:
            values = config.generate_email(self.id)
            mail = mail_obj.create(values)
            if mail:
                mail.send()
    
    
    @api.multi
    def action_validate(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if any(holiday.state not in ['confirm', 'validate1'] for holiday in self):
            raise UserError(_('Leave request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})
        self.send_hr_approved_mail()
        self.filtered(lambda holiday: holiday.validation_type == 'both').write({'second_approver_id': current_employee.id})
        self.filtered(lambda holiday: holiday.validation_type != 'both').write({'first_approver_id': current_employee.id})

        for holiday in self.filtered(lambda holiday: holiday.holiday_type != 'employee'):
            if holiday.holiday_type == 'category':
                employees = holiday.category_id.employee_ids
            elif holiday.holiday_type == 'company':
                employees = self.env['hr.employee'].search([('company_id', '=', holiday.mode_company_id.id)])
            else:
                employees = holiday.department_id.member_ids

            if self.env['hr.leave'].search_count([('date_from', '<=', holiday.date_to), ('date_to', '>', holiday.date_from),
                               ('state', 'not in', ['cancel', 'refuse']), ('holiday_type', '=', 'employee'),
                               ('employee_id', 'in', employees.ids)]):
                raise ValidationError(_('You can not have 2 leaves that overlaps on the same day.'))

            values = [holiday._prepare_holiday_values(employee) for employee in employees]
            leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
            ).create(values)
            leaves.action_approve()
            # FIXME RLi: This does not make sense, only the parent should be in validation_type both
            if leaves and leaves[0].validation_type == 'both':
                leaves.action_validate()

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.activity_update()
        return True
    
    @api.multi
    def send_leave_notification_mail(self):

        employees = self.env['hr.leave'].search([])
        
        current_dates = False
        
        for self in employees:
            if self.date_from:
                
                current_dates = datetime.datetime.strptime(self.date_from, "%Y-%m-%d")
                current_datesz = current_dates - relativedelta(days=3)
                
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
                            config = self.env['mail.template'].sudo().search([('name','=','Leave Reminder')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
                                return True
        return


class EmployeeContract(models.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'
    
    trial_date_end_bool = fields.Boolean(string="Update Probation", store=True)
    prorate_salary = fields.Boolean(string='Prorate Salary')
    
    @api.onchange('trial_date_end')
    def send_notification(self):
        self.trial_date_end_bool = True
    
    @api.multi
    def write(self, vals):
        result = super(EmployeeContract, self).write(vals)
        return result
    
    enabled_for_pension = fields.Boolean(string="Enabled for Pension")
    enabled_for_nhf = fields.Boolean(string="Enabled for NHF")
    loan_enabled = fields.Boolean(string="Loan enabled")
    outstanding_loan = fields.Float(string="Outstanding loan")
    additional_pension_contributions = fields.Float(string="Additional pension contributions")
    enabled_for_annual_bonus = fields.Boolean(string="Enabled for Annual Bonus")
    enabled_for_overtime = fields.Boolean(string="Enabled for Overtime")
    training_social_membership = fields.Float(string="Training & social Membership Allw.(%)")
    communication_allw = fields.Float(string="Communication Allw.(%)")
    feeding_allw = fields.Float(string="Feeding Allw.(%)")
    housing_allw = fields.Float(string="Housing(%)")
    transport_allw = fields.Float(string="Transport(%)")
    basic = fields.Float(string="Basic(%)")
    annual_salary = fields.Float(string="Annual Salary")
    
    @api.multi
    def send_anniversary_mail(self):
        
        test = False
        employees = self.env['hr.contract'].search([])
        
        for self in employees:
            if self.employee_id.active == True:
                if self.date_start:
                    test = datetime.datetime.strptime(str(self.date_start), "%Y-%m-%d")
                    
                    date_start_day = test.day
                    date_start_month = test.month
                    
                    today = datetime.datetime.now().strftime("%Y-%m-%d")
                    
                    test_today = datetime.datetime.today().strptime(today, "%Y-%m-%d")
                    date_start_day_today = test_today.day
                    date_start_month_today = test_today.month
                    
                    
                    if date_start_month == date_start_month_today:
                        if date_start_day == date_start_day_today:
                            config = self.env['mail.template'].sudo().search([('name','=','Work Annivasary')], limit=1)
                            mail_obj = self.env['mail.mail']
                            if config:
                                values = config.generate_email(self.id)
                                mail = mail_obj.create(values)
                                if mail:
                                    mail.send()
                                return True
        return

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'
    
    @api.multi
    def close_payslip_run(self):
        self.slip_ids.action_payslip_done()
        return self.write({'state': 'close'})

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    prorate_days = fields.Float(string='Proration Days', required=False, help="Proration Days")
    
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