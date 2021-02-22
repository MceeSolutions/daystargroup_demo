# -*- coding: utf-8 -*-

import datetime
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from ast import literal_eval
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo import api, fields, models, _
from email.policy import default


class ItemType(models.Model):
    
    def find_missing(self,lst): 
        return [x for x in range(lst[0], lst[-1]+2)  
                               if x not in lst] 

    
    def _default_code(self):
        code  = [int(a.code) for a in self.search([(1,'=',1)])]
        if code ==[]:
            return '001'
        else:
            return str(self.find_missing(code)[0]).zfill(3)
 
    
    _name = "item.type"
    _description = "Item Types"
    _order = "code"
    _inherit = ['mail.thread']

    name = fields.Char('Name', required=True, track_visibility='onchange')
    code = fields.Char('Code', required=True, default=_default_code, track_visibility='onchange')
    active = fields.Boolean('Active', default='True')


class BrandType(models.Model):
    
    def find_missing(self,lst): 
        return [x for x in range(lst[0], lst[-1]+2)  
                           if x not in lst] 

    def _default_code(self):
        code  = [int(a.code[1:]) for a in self.search([(1,'=',1)])]
        if code ==[]:
            return 'M0001'
        else:
            return 'M' + str(self.find_missing(code)[0]).zfill(4)
    _name = "brand.type"
    _description = "Manufacturer"
    _order = "code"
    _inherit = ['mail.thread']

    name = fields.Char('Name', required=True, track_visibility='onchange')
    code = fields.Char('Code', required=True, default=_default_code, track_visibility='onchange')
    active = fields.Boolean('Active', default='True')
