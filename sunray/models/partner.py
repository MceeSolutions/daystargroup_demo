from ast import literal_eval
from odoo import models, fields, api, _


class Partners(models.Model):
    _inherit = 'res.partner'
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('validate', 'Second Approval'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice address'),
         ('delivery', 'Shipping address'),
         ('other', 'Sub Account'),
         ("private", "Private Address"),
        ], string='Address Type',
        default='contact',
        help="Used by Sales and Purchase Apps to select the relevant address depending on the context.")
    
    name = fields.Char(index=True, track_visibility="onchange")
    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks', track_visibility="onchange")
    email = fields.Char(track_visibility="onchange")
    tax_compliance = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Tax compliance', required=False)
    due_diligence_form = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Due Diligence Form', required=False)
    cac = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='CAC', required=False)
    delivery_speed = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Delivery Speed')
    overall_vendor_rating = fields.Selection([('0', '0'),('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], string='Overall Vendor Rating', required=False)
    parent_account_number = fields.Char(string='Customer Code', required=False, index=True, copy=False, store=True)
    vendor_registration = fields.Boolean ('Vendor fully Registered', track_visibility="onchange", readonly=True)
    customer_registration = fields.Boolean ('Customer fully Registered', track_visibility="onchange", readonly=True)
    tin = fields.Char(string='Tin', required=False, index=True, copy=False, store=True)
    wht_rate = fields.Float(string='WHT Rate', required=False, index=True, copy=False, store=True)
    transaction_class = fields.Selection([('suply', 'Supply'),('service', 'Service'), ('contract', 'Contract'), ('licencing', 'Licencing'), ('rent', 'Rent'), ('prof', 'Professional/Consultancy service')], string='Transaction Class', required=False, index=True, copy=False, store=True)
    transaction_authority = fields.Char(string='Tax Authoritiy', required=False, index=True, copy=False, store=True)
    iban = fields.Char(string='IBAN', required=False, index=True, copy=False, store=True)
    transaction_description = fields.Char(string='Transaction Description', required=False, index=True, copy=False, store=True)
    site_code_count = fields.Integer(compute="_site_code_count",string="Site Code(s)", store=False)
    building_no = fields.Char(string="Building No.")
    office_no = fields.Char(string="Office No.")
    postal_code = fields.Char(string="Postal Code")
    district = fields.Char(string="District/ Region")
    rc = fields.Char(string="RC or Business registration number")
    vat_eligible = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="VAT eligibility")
    business_legal_structure = fields.Selection([('joint', 'Joint Stock Company'), ('limited', 'Limited Liability Company'), ('non', 'Non-Profit organization'), ('public', 'Public Liability Company'), ('trust', 'Business Trust'), ('other', 'Other')], 
                                                string="Business Legal Structure")
    vat_no = fields.Char(string="Vat No")
    tax_no = fields.Char(string="Tax No.")
    legal = fields.Char(string="Other, Please specify:")
    customer = fields.Boolean(string='Is a Customer', default=False,
                               help="Check this box if this contact is a customer. It can be selected in sales orders.")
    # potential_customer = fields.Boolean(string='Potential Customer', default=False,
    #                                     help="Check this box if this contact is a potential customer. It can be selected in sales orders.") lekan
    employee = fields.Boolean(string='Employee')
    daystar_companies = fields.Boolean(string='Daystar Companies')
    stored_display_name = fields.Char(string="stored_display_name")
    customer_type_id = fields.Many2one(comodel_name='customer.type', string='Customer Type')

    @api.multi
    def _site_code_count(self):
        oe_checklist = self.env['site.code']
        for pa in self:
            domain = [('partner_id', '=', pa.id)]
            pres_ids = oe_checklist.search(domain)
            pres = oe_checklist.browse(pres_ids)
            issues_count = 0
            for pr in pres:
                issues_count+=1
            pa.site_code_count = issues_count
        return True
    
    @api.multi
    def _check_potential_customer(self, vals):
        if 'potential_customer' in vals and vals['potential_customer'] == True:
            if not self.user_has_groups('sunray.group_potential_customer_creation'):
                raise UserError(_("Only Members of the BD/Sales team can create Potential Customer(s)"))
            else:
                print('nothing')
    
    @api.multi
    def _check_customer_code(self, vals):
        return True

    @api.model
    def create(self, vals):
        self._check_customer_code(vals)
        # self._check_potential_customer(vals)
        return super(Partners, self).create(vals)
        
    @api.multi
    def name_get(self):
        res = []
  
        for partner in self:
            result = partner.name
            if partner.parent_account_number:
                result = str(partner.name) + " " + str(partner.parent_account_number)
            res.append((partner.id, result))
        return res
    
    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return {}
    
    @api.multi
    def button_submit(self):
        self.write({'state': 'submit'})
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_one_vendor_approval')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This Vendor {} needs first approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_validate(self):
        self._check_line_manager()
        self.write({'state': 'validate'})
        group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_two_vendor_approval')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "This Vendor {} needs second approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_approve(self):
        self.write({'state': 'approve'})
        self.vendor_registration = True
        return {}
    
    @api.multi
    def button_reject(self):
        self.write({'state': 'reject'})
        return {}
    
    #this is the vendor checklist
    completed_vendor_information = fields.Boolean(string="COMPLETED VENDOR INFORMATION FORM (AS  ATTACHED)")
    report_of_proposers_follow_up = fields.Boolean(string="REPORT OF PROPOSER'S FOLLOW UP REVIEW OF SECTIONS 4 & 5")
    true_copy_incorporation = fields.Boolean(string="COPY OF CERTIFICATE OF INCORPORATION / BUSINESS NAME REGISTRATION CERTIFICATE")
    true_copy_memorandum = fields.Boolean(string="CERTIFIED TRUE COPY OF MEMORANDUM AND ARTICLE OF  ASSOCIATION FOR LIMITED LIABILITY COMPANIES")
    true_copy_form_c02 = fields.Boolean(string="CERTIFIED TRUE COPY OF FORM C02 AND C07 FOR LIMITED LIABILITY COMPANIES")
    Vat_cert = fields.Boolean(string="VAT CERTIFICATE / FIRS REGISTRATION CERTIFICATE")
    sign_and_stamp = fields.Boolean(string="SIGN AND STAMP THE FOLLOWING SUNRAY VENRURES GENERAL TERMS & CONDITIONS BY AUTHORIZED STAFF")

    current_dpr = fields.Boolean(string="CURRENT DPR CERTIFICATE (If Applicable)")
    commercial_certificate = fields.Boolean(string="COMMERCIAL PROPOSAL OR WEBSITE REVIEW (COMPANY PROFILE INCLUDING DETAILS OF MANAGEMENT TEAM, REFERENCES & CASE STUDIES)")
    proposers_report = fields.Boolean(string="PROPOSER'S REPORT CONFIRMING CLEAN REVIEW ON INTERNET & OTHER AVAILABLE SOURCES (IF NOT CLEAN, FURTHER INFORMATION ON MATTERS IDENTIFIED)")
    copies_of_required_specialist = fields.Boolean(string="COPIES OF REQUIRED SPECIALIST CERTIFICATIONS, REGISTRATIONS & LICENCES (If Applicable)")

    recommendation_letters_from_applicant = fields.Boolean(string="RECOMMENDATION LETTER FROM APPLICANT BANKERS IN RESPECT TO THE OPERATION OF HIS/HER COMPANY'S ACCOUNT")
    evidence_of_tax = fields.Boolean(string="EVIDENCE OF TAX PAYMENT")
    code_of_conduct = fields.Boolean(string="CODE OF CONDUCT AND CODE OF ETHICS - SIGNED BY THE COMPANY'S MD OR AUTHORIZED STAFF")
    specific_references = fields.Boolean(string="SPECIFIC REFERENCES")
    latest_financials = fields.Boolean(string="LATEST FINANCIAL STATEMENTS / KEY KPIs")
    
    completed_customer_information = fields.Boolean(string="COMPLETED CUSTOMER INFORMATION FORM (AS  ATTACHED)")
    
    @api.multi
    def button_select_all(self):
        self.write({'completed_vendor_information': True})
        self.write({'report_of_proposers_follow_up': True})
        self.write({'true_copy_incorporation': True})
        self.write({'true_copy_memorandum': True})
        self.write({'true_copy_form_c02': True})
        self.write({'Vat_cert': True})
        self.write({'sign_and_stamp': True})
        self.write({'current_dpr': True})
        self.write({'commercial_certificate': True})
        self.write({'proposers_report': True})
        self.write({'copies_of_required_specialist': True})
        self.write({'evidence_of_tax': True})
        self.write({'recommendation_letters_from_applicant': True})
        self.write({'code_of_conduct': True})
        self.write({'specific_references': True})
        self.write({'latest_financials': True})
        return {}
    
    @api.multi
    def open_customers_site_code(self):
        self.ensure_one()
        action = self.env.ref('sunray.site_location_action_window').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.id))
        return action
