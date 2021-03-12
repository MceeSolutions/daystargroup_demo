from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
        for sale in self:
            if sale.origin:
                if "SO0" in sale.origin:
                    sale.from_sale = True
            
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
            if not assets.account_analytic_id:
                assets.account_analytic_id = assets.site_code_id.project_id.analytic_account_id
            if not assets.asset_partner_id:
                assets.asset_partner_id = self.site_code_id.partner_id


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    
    department_id = fields.Many2one(comodel_name='hr.department', string='Department')


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