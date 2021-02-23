from odoo import models, fields, api


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