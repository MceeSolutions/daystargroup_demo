# -*- coding: utf-8 -*-
import datetime

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import email_split, float_is_zero
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


from odoo.addons import decimal_precision as dp

class Picking(models.Model):
    _name = "stock.picking"
    _inherit = 'stock.picking'
    
    def _default_picking_type_id(self): 
        type = self.env['stock.picking.type'].search([('code','=','outgoing')], limit=1)
        return type
    
    @api.one
    @api.depends('site_code_id','site_code_id.project_id')
    def _get_analytic_account(self):
        if self.site_code_id.project_id.account_analytic_id:
            self.analytic_account_id = self.site_code_id.project_id.account_analytic_id.id
    
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
    
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}, default=_default_picking_type_id)
    
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

   
class StockMove(models.Model):
    _inherit = "stock.move"
    
    @api.one
    @api.depends('product_uom_qty', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            self.price_subtotal = self.product_uom_qty * line.price_unit
    
    def _default_cost(self):
        return self.product_id.standard_price
    
    @api.multi
    @api.onchange('product_id','product_uom_qty')
    def product_change(self):
        self.price_unit = self.price_cost
        self.price_subtotal = self.product_uom_qty * self.price_unit
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
    
    analytic_account_id = fields.Many2one(
        related='picking_id.analytic_account_id', store=True)
    account_id = fields.Many2one('account.account', string='Account', index=True, ondelete='cascade')
    price_cost = fields.Float(string="Cost", related='product_id.standard_price')
    price_subtotal = fields.Float(string="Price Subtotal", compute="_compute_subtotal", readonly=True)

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    analytic_account_id = fields.Many2one(
<<<<<<< HEAD
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

# class MaintenanceRequest(models.Model):
#     _inherit = 'maintenance.request'
    
#     site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
#     product_id = fields.Many2one(comodel_name='product.product', string='Product')
    
#     @api.multi
#     def create_repair_request(self):
#         """
#         Method to open create repair order form
#         """
                     
#         view_ref = self.env['ir.model.data'].get_object_reference('repair', 'view_repair_order_form')
#         view_id = view_ref[1] if view_ref else False
         
#         res = {
#             'type': 'ir.actions.act_window',
#             'name': ('Repair Order'),
#             'res_model': 'repair.order',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'view_id': view_id,
#             'target': 'current',
#             #'context': {'default_origin': self.name, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id, 'default_move_lines': order_lines}
#         }
        
#         return res
    
#     @api.multi
#     def create_store_request(self):
#         """
#         Method to open create store request form
#         """
             
#         view_ref = self.env['ir.model.data'].get_object_reference('sunray', 'sunray_stock_form_view')
#         view_id = view_ref[1] if view_ref else False
         
#         res = {
#             'type': 'ir.actions.act_window',
#             'name': ('Store Request'),
#             'res_model': 'stock.picking',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'view_id': view_id,
#             'target': 'current',
#             'context': {'default_origin': self.name, "default_is_locked":False, "default_picking_type_id":self.env.ref("sunray.stock_picking_type_emp").id}
#         }        
#        return res

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





             
    
=======
        related='move_id.analytic_account_id')
>>>>>>> demo
