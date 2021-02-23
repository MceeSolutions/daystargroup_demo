from odoo import models, fields, api, _


class parkpreliminary(models.Model):
    _name = 'parking.list'
    _description = 'Parking List'
   
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])

    date = fields.Date(string='Date')
    request_no = fields.Char(string='Request Number')
    site = fields.Char(string='Site')
    requester = fields.Char(string='Requester')
    reciever_id = fields.Many2one(comodel_name='hr.employee', string='Received By', default=_default_employee)
    receiver_sign_date = fields.Date(string='Receivers Date', default=date.today())
    line_ids = fields.One2many(comodel_name='parking.list.line',inverse_name='parking_id', string='Parking ID')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee Name', default=_default_employee) #used as a signature to pull the currently employee    
    employee_sign_date = fields.Date(string='Employees Date', default=date.today())# used as a signature date. 
    security_id = fields.Many2one(comodel_name='hr.employee', string='Security Name', default=_default_employee) #used as a signature to pull the currently employee    
    security_sign_date = fields.Date(string='Securitys Date', default=date.today())# used as a signature date. 


class parkinglistreport(models.Model):
    _name = 'parking.list.line'
    _description = 'Parking List Line'

    parking_id = fields.Many2one(comodel_name='hr.employee')
    serial_no = fields.Char(string='Serial No')
    item = fields.Char(string='Items')
    part_no = fields.Char(string='Part Number')
    quantity = fields.Char(string='Quantity')
    packaging = fields.Char(string='Partackaging') 
