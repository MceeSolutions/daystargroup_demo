from odoo import models, fields, api, _


class SubAccount(models.Model):
    _name = "sub.account"
    _description = "sub account form"
    _order = "parent_id"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    
    @api.multi
    def name_get(self):
        res = []
        for partner in self:
            result = partner.name
            if partner.child_account:
                result = str(partner.name) + " " + str(partner.child_account)
            res.append((partner.id, result))
        return res
    
    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))

    def _default_company(self):
        return self.env['res.company']._company_default_get('res.partner')
            
    def _compute_company_type(self):
        for partner in self:
            partner.company_type = 'company' if partner.is_company else 'person'

    name = fields.Char(index=True, track_visibility='onchange')
    parent_id = fields.Many2one('res.partner', string='Customer', domain="[('customer','=',True)]", index=True, ondelete='cascade', track_visibility='onchange')
    function = fields.Char(string='Description')
    comment = fields.Text(string='Desription')
    addinfo = fields.Text(string='Additional Information')
    child_account = fields.Char(string='Child Account Number', index=True, copy=False, default='/', track_visibility='onchange')
    website = fields.Char(help="Website of Partner or Company")
    employee = fields.Boolean(help="Check this box if this contact is an Employee.")
    fax = fields.Char(help="fax")
    create_date = fields.Date(string='Create Date', readonly=True, track_visibility='onchange')
    activation_date = fields.Date(string='Activation Date', readonly=False, track_visibility='onchange')
    term_date = fields.Date(string='Termination Date', track_visibility='onchange')
    perm_up_date = fields.Date(string='Permanent Activation Date', readonly=False, track_visibility='onchange')
    price_review_date = fields.Date(string='Price Review Date', readonly=False, track_visibility='onchange')
    contact_person = fields.Many2one('res.partner.title')
    company_name = fields.Many2many('Company Name')
    employee = fields.Boolean(help="Check this box if this contact is an Employee.")
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice address'),
         ('delivery', 'Shipping address'),
         ('other', 'Other address')], string='Address Type',
        default='invoice',
        help="Used to select automatically the right address according to the context in sales and purchases documents.")
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    email = fields.Char()
    phone = fields.Char()
    mobile = fields.Char()
    company_type = fields.Selection(string='Company Type',
        selection=[('person', 'Individual'), ('company', 'Company')],
        compute='_compute_company_type', inverse='_write_company_type')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=_default_company)
    contact_address = fields.Char(compute='_compute_contact_address', string='Complete Address')
    company_name = fields.Char('Company Name') 
    state = fields.Selection([
        ('new', 'Waiting Approval'),
        ('approve', 'Approved'),
        ('activate', 'Activated'),
        ('suspend', 'Suspended'),
        ('terminate', 'Terminated'),
        ('cancel', 'Canceled'),
        ('reject', 'Rejected'),
        ], string='Status', index=True, copy=False, default='new', track_visibility='onchange')

    @api.model
    def create(self, vals):
        partner_ids = self.search([('parent_id','=',vals['parent_id'])],order="child_account desc")
        for p in  partner_ids:
            print(p.child_account)
        if not partner_ids:
            vals['child_account'] = "SA001"
        else:
            number = partner_ids[0].child_account.split("A",2)
            number = int(number[1]) + 1
            vals['child_account'] = "SA" + str(number).zfill(3)
        return super(SubAccount, self).create(vals)
    
    
    @api.multi
    def button_new(self):
        self.write({'state': 'new'})
        return {}
    
    @api.multi
    def button_activate(self):
        self.write({'state': 'activate'})
        return {}
    
    @api.multi
    def button_suspend(self):
        self.write({'state': 'suspend'})
        return {}
    
    @api.multi
    def button_terminate(self):
        self.write({'state': 'terminate'})
        self.term_date = date.today()
        return {}
    
    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancel'})
        return {}
    
    @api.multi
    def button_approve(self):
        self.write({'state': 'approve'})
        return {}
    
    @api.multi
    def button_reject(self):
        self.write({'state': 'reject'})
        return {}
