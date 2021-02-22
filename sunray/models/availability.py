from odoo import models, fields, api, _


class AvailabilityRequest(models.Model):
    _name = "availability.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Availability Demand Form"
    
    name = fields.Char('Order Reference', readonly=True, required=True, index=True, copy=False, default='New')    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    
    def _default_employee(self):
        self.env['hr.employee'].search([('user_id','=',self.env.uid)])
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)])
    
    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return {}
    
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        return {}
    
    @api.multi
    def button_approve(self):
        self.write({'state': 'approve'})
        '''vals = {
            'name' : self.name,
            'company_type' : self.company_type,
            'image' : self.image,
            'parent_id' : self.parent_id.id,
            'street' : self.street,
            'street2' : self.street2,
            'city' : self.city,
            'state_id' : self.state_id.id,
            'zip' : self.zip,
            'country_id' : self.country_id.id,            
            'vat' : self.vat,
            'function' : self.function,
            'phone' : self.phone,
            'mobile' : self.mobile,
            'email' : self.email,
            'customer': self.customer,
            'supplier' : self.supplier,
            'supplier' : self.company_id.id
        }
        self.env['res.partner'].create(vals)
        '''
        return {}
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('availability.request') or '/'
        return super(AvailabilityRequest, self).create(vals)
    
    @api.multi
    def create_purchase_order(self):
        """
        Method to open create purchase order form
        """

        partner_id = self.request_client_id
        client_id = self.request_client_id
        view_ref = self.env['ir.model.data'].get_object_reference('purchase', 'purchase_order_form')
        view_id = view_ref[1] if view_ref else False
        
        for subscription in self:
            order_lines = []
            for line in subscription.request_move_line:
                order_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'account_id': line.product_id.property_account_expense_id.id,
                    'account_analytic_id': 1,
                    'product_qty': line.product_oum_qty,
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
            'context': {'default_client_id': client_id.id, 'default_stock_source': self.name, 'default_order_line': order_lines}
        }
        
        return res
    
    @api.multi
    def create_store_request(self):
        """
        Method to open create purchase order form
        """

        partner_id = self.request_client_id
        client_id = self.request_client_id     
        view_ref = self.env['ir.model.data'].get_object_reference('sunray', 'sunray_stock_form_view')
        view_id = view_ref[1] if view_ref else False
        
        for subscription in self:
            order_lines = []
            for line in subscription.request_move_line:
                order_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_oum_qty,
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
            'context': {'default_client_id': client_id.id, 'default_origin': self.name, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id, 'default_move_lines': order_lines}
        }
        
        return res
    
    requestor_id = fields.Many2one('hr.employee', 'Requesting Employee', default=_default_employee, help="Default Owner")
    department_name = fields.Char(string="Department", related="requestor_id.department_id.name", readonly=True)    
    request_client_id = fields.Many2one('res.partner', string='Clients', index=True, ondelete='cascade', required=False)
    request_date = fields.Datetime(string="Due Date")
    request_move_line = fields.One2many('availability.request.line', 'availability_id', string="Stock Move", copy=True)


class AvailabilityRequestLine(models.Model):
    _name = "availability.request.line"
    _description = 'Availability Request Line'
    
    availability_id = fields.Many2one('availability.request', 'Availability Demand Form')
    product_id = fields.Many2one('product.product', 'Product')
    product_oum_qty = fields.Float(string="Quantity")
    price_cost  = fields.Float(string="Cost", related="product_id.standard_price")