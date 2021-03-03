from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('manager_approval', 'Management Approval'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3, default='draft')
    
    need_management_approval = fields.Boolean('Needs Management Approval', track_visibility="onchange", copy=False, default=False)
    
    @api.multi
    def action_cancel(self):
        sub = self.env['sale.subscription'].search([('stage_id.name','=','In Progress'), ('partner_id', '=', self.partner_id.id), ('sale_order_id', '=', self.id)])
        if sub:
            sub.write({'stage_id': 4})
        return self.write({'state': 'cancel'})
    
    @api.multi
    def _check_customer_registration(self):
        if self.partner_id.customer_registration == False:
            raise UserError(_('Cant Confirm sale order for an unregistered customer -- Request Customer Registration.'))

    
    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self._check_customer_registration()
        return res
    
    @api.depends('amount_total')
    def _check_approval(self):
        if self.amount_total > 10.00:
            self.need_management_approval = True
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_sale_account_budget')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Sales Order {} needs management approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
            return self.state
        else:
            self.need_approval = False
            
    def _prepare_subscription_data(self, template):
        """Prepare a dictionnary of values to create a subscription from a template."""
        self.ensure_one()
        values = {
            'name': template.name,
            'template_id': template.id,
            'partner_id': self.partner_invoice_id.id,
            'sale_order_id': self.id,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'date_start': fields.Date.today(),
            'description': self.note or template.description,
            'pricelist_id': self.pricelist_id.id,
            'company_id': self.company_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'payment_token_id': self.transaction_ids.get_last_transaction().payment_token_id.id if template.payment_mode in ['validate_send_payment', 'success_payment'] else False
        }
        default_stage = self.env['sale.subscription.stage'].search([('in_progress', '=', True)], limit=1)
        if default_stage:
            values['stage_id'] = default_stage.id
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[template.recurring_rule_type]: template.recurring_interval})
        recurring_next_date = today + invoicing_period
        values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)
        return values
    

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _description = 'Sales Order Line'
    _inherit = ['sale.order.line']
    
    @api.onchange('site_code_id')
    def _onchange_partner_id(self):
        self.analytic_account_id = self.site_code_id.project_id.analytic_account_id
        return {}
    
    type = fields.Selection([('sale', 'Sale'), ('lease', 'Lease')], string='Type', required=True, default='sale')
    project_id = fields.Many2one(comodel_name="project.project", string="Site Location")
    site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
    
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False)
    
    def _prepare_subscription_line_data(self):
        """Prepare a dictionnary of values to add lines to a subscription."""
        values = list()
        for line in self:
            values.append((0, False, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'uom_id': line.product_uom.id,
                'price_unit': line.price_unit,
                'site_code_id': line.site_code_id.id,
                'discount': line.discount if line.order_id.subscription_management != 'upsell' else False,
            }))
        return values
    
    @api.multi
    def _timesheet_create_project(self):
        """ Generate project for the given so line, and link it.
            :param project: record of project.project in which the task should be created
            :return task: record of the created task
        """
        self.ensure_one()
        account = self.order_id.analytic_account_id
        if not account:
            self.order_id._create_analytic_account(prefix=self.product_id.default_code or None)
            account = self.order_id.analytic_account_id

        # create the project or duplicate one
        values = {
            'name': '%s - %s' % (self.order_id.client_order_ref, self.order_id.name) if self.order_id.client_order_ref else self.site_code_id.name + " " + "-" + " " + self.order_id.partner_id.name + " - " + self.site_code_id.site_area,
            'allow_timesheets': True,
            'analytic_account_id': account.id,
            'partner_id': self.order_id.partner_id.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'site_code_id': self.site_code_id.id,
            'site_area': self.site_code_id.site_area,
            'site_location_id': self.site_code_id.state_id.id,
            'active': True,
        }
        if self.product_id.project_template_id:
            values['name'] = "%s - %s" % (values['name'], self.product_id.project_template_id.name)
            project = self.product_id.project_template_id.copy(values)
            project.tasks.write({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id,
                'email_from': self.order_id.partner_id.email,
            })
            # duplicating a project doesn't set the SO on sub-tasks
            project.tasks.filtered(lambda task: task.parent_id != False).write({
                'sale_line_id': self.id,
            })
        else:
            project = self.env['project.project'].create(values)
        # link project as generated by current so line
        self.write({'project_id': project.id})
        return project

# class SaleSubscription(models.Model):
#     _inherit = "sale.subscription"
    
#     sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')

# class SaleSubscriptionLine(models.Model):
#     _inherit = "sale.subscription.line"
    
#     site_code_id = fields.Many2one(comodel_name="site.code", string="Site Code")
#     account_analytic_id = fields.Many2one(comodel_name='account.analytic.account', string="Analytic Account", copy=False)
    