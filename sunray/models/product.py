from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    business_unit = fields.Char(string='Business Unit')
    manufacturer = fields.Char(string='Manufacturer')
    dimension = fields.Char(string='Dimension (mm) (W x D x H)')
    manufacturer_part_number = fields.Char(string='Manufacturer part number')    
    brand = fields.Many2one('brand.type', string='Manufacturer', track_visibility='onchange', index=True)
    item_type = fields.Many2one('item.type', string='Item Type', track_visibility='onchange', index=True)


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

