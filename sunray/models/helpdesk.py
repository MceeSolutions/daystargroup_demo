from odoo import models, fields, api


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"
    _description = 'Ticket'
    
    project_id = fields.Many2one(comodel_name='project.project', string='Project')
    project_site_code_id = fields.Many2one(comodel_name='site.code', string='Site Code', related='project_id.site_code_id', store = True)
    stage_name = fields.Char(string='Stage Name', related='stage_id.name', store = True)
    
    @api.onchange('stage_id')
    def _check_security_action_validate(self):
        if self.stage_id.name == 'Solved':
            if not self.env.user.has_group('sunray.group_noc_team'):
                raise UserError(_('Only members of the Noc Team are allowed to close tickets.'))
    
    @api.multi
    def button_request_closure(self):
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_noc_team')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This Ticket '{}' is ready for closure".format(self.display_name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
