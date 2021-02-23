from odoo import models, fields, api, _


class IrSequence(models.Model):
    _inherit = 'ir.sequence'
    
    @api.multi
    def _check_po_sequence(self):
        po_code = self.env['ir.sequence'].search([('code', '=', 'purchase.order')], limit=1)
        if po_code:
            po_code.number_next_actual = 1
