from odoo import models, fields, api


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
    