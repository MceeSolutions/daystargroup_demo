from datetime import date
from odoo import models, fields, api, _


class Expreliminary(models.Model):
    _name = 'expense.report'
    _description = 'Expense Report'
   
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])
    
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', default=_default_employee) #used as a signature to pull the currently employee    
    employee_sign_date = fields.Date(string='Employee Sign Date', default=date.today())# used as a signature date.
    name = fields.Char(string='Name')
    purpose = fields.Char(string='Purpose')
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    expense_advanced = fields.Integer(string= 'Expense Advanced')
    balance_company = fields.Integer(string='Balance due To Employee')
    balance_employee = fields.Integer(string='Balance due to Company')
    total_expense = fields.Integer(string='Total Expense')
    line_ids = fields.One2many('expense.report.line','expense_id',string='Expenses')
    day = fields.Selection(related = 'line_ids.day', string='Day')
    date = fields.Date(related = 'line_ids.date', string='Date')
    description = fields.Char(related = 'line_ids.description', string='Description')
    expense = fields.Integer(related = 'line_ids.expense', string=' Total Expense')
    receipt = fields.Selection(related = 'line_ids.receipt', string='receipt')


class businessexpensereport(models.Model):
    _name = 'expense.report.line'
    _description = 'Expense Report Line'

    expense_id = fields.Many2one(comodel_name='expense.report', string="Expense id")
    date = fields.Date(string='Date')
    day = fields.Selection([
        ('monday','Monday'),
        ('tuesday','Tuesday'),
        ('wednesday','Wednesday'),
        ('thursday','Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')],
        string='Day',
        required=True)
    description = fields.Char(string='Description')
    expense = fields.Integer(string='Expense')
    receipt = fields.Selection([
            ('yes','Yes'),
            ('no','No')],
            string='Receipt Available',
            required=True)