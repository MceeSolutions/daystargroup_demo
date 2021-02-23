from ast import literal_eval
from odoo import models, fields, api, _


class VendorRequest(models.Model):
    _name = "vendor.request"
    _description = "Contact Request"
    _order = "name"
    _inherit = ['res.partner']
    
    @api.multi
    def _message_add_suggested_recipient(self, result, partner=None, email=None, reason=''):
        """ Called by message_get_suggested_recipients, to add a suggested
            recipient in the result dictionary. The form is :
                partner_id, partner_name<partner_email> or partner_name, reason """
        self.ensure_one()
        if email and not partner:
            # get partner info from email
            partner_info = self.message_partner_info_from_emails([email])[0]
            if partner_info.get('partner_id'):
                partner = self.env['res.partner'].sudo().browse([partner_info['partner_id']])[0]
        if email and email in [val[1] for val in result[self.ids[0]]]:  # already existing email -> skip
            return result
        if partner and partner in self.message_partner_ids:  # recipient already in the followers -> skip
            return result
        if partner and partner.id in [val[0] for val in result[self.ids[0]]]:  # already existing partner ID -> skip
            return result
        if partner and partner.email:  # complete profile: id, name <email>
            result[self.ids[0]].append((partner.id, '%s<%s>' % (partner.name, partner.email), reason))
        elif partner:  # incomplete profile: id, name
            result[self.ids[0]].append((partner.id, '%s' % (partner.name), reason))
        else:  # unknown partner, we are probably managing an email address
            result[self.ids[0]].append((False, email, reason))
        return result
    
    def _default_employee(self): # this method is to search the hr.employee and return the user id of the person clicking the form atm
        return self.env['hr.employee'].search([('user_id','=',self.env.uid)], limit=1)
    
    @api.multi
    def _check_line_manager(self):
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if current_employee == self.employee_id:
            raise UserError(_('You are not allowed to approve your own request.'))
    
    @api.multi
    def _check_customer_code(self, vals):
        customer = self.env['res.partner'].search([('parent_account_number','=',vals['parent_account_number'])])
        if vals['parent_account_number'] == False:
            print('proceed')
        else:
            if customer:
                raise UserError(_('Customer Code Must Unique!'))
        
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_info', 'Pending Partner info'),
        ('approve', 'Pending Approval 1'),
        ('validate', 'pending Final Approval'),
        ('registered', 'Registered'),
        ('reject', 'Rejected'),
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    parent_account_number = fields.Char(string='Customer Code', index=True, copy=False, store=True, readonly=False, states={'validate': [('readonly', False)]})
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Requesting Employee', default=_default_employee)
    vendor_registration = fields.Boolean ('Vendor fully Registered', track_visibility="onchange", readonly=True)
    customer_registration = fields.Boolean ('Customer fully Registered', track_visibility="onchange", readonly=True)
    checklist_count = fields.Integer(compute="_checklist_count",string="Checklist", store=False)
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
    legal_review = fields.Boolean(string='Legal Review')
    legal_review_done = fields.Boolean(string='Legal Review Done')
    contact_email = fields.Char(string="email")
    completed_customer_information = fields.Boolean(string="COMPLETED CUSTOMER INFORMATION FORM (AS  ATTACHED)")
    
    #futher Vendor details
    building_no = fields.Char(string="Building No.")
    office_no = fields.Char(string="Office No.")
    postal_code = fields.Char(string="Postal Code")
    district = fields.Char(string="District/ Region")
    country_id = fields.Many2one(comodel_name='res.country', string="Country")
    rc = fields.Char(string="RC or Business registration nb")
    vat_eligible = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="VAT eligibility")
    business_legal_structure = fields.Selection([('joint', 'Joint Stock Company'), ('limited', 'Limited Liability Company'), ('non', 'Non-Profit organization'), ('public', 'Public Liability Company'), ('trust', 'Business Trust'), ('other', 'Other')], 
                                                string="Business Legal Structure")
    vat_no = fields.Char(string="Vat No")
    tax_no = fields.Char(string="Tax No.")
    legal = fields.Char(string="Other, Please specify:")
    customer = fields.Boolean(string='Is a Customer', default=False, help="Check this box if this contact is a customer.")
    supplier = fields.Boolean(string='Is a Vendor', default = True, help="Check this box if this contact is a vendor.")
    street = fields.Char()
    city = fields.Char()
    company_type = fields.Selection(string='Company Type',
        selection=[('company', 'Company'), ('person', 'Individual')], default='company')
    
    potential_partner_id = fields.Many2one(comodel_name='res.partner', string="Potential Customer")
    customer_type_id = fields.Many2one(comodel_name='customer.type', string='Customer Type')
    
    @api.onchange('potential_partner_id')
    def _onchange_opportunity_create_date(self):
        self.name = self.potential_partner_id.name
        self.contact_email = self.potential_partner_id.email
        self.parent_account_number = self.potential_partner_id.parent_account_number
        self.building_no = self.potential_partner_id.building_no
        self.office_no = self.potential_partner_id.office_no
        self.postal_code = self.potential_partner_id.postal_code
        self.street = self.potential_partner_id.street
        self.vat_no = self.potential_partner_id.vat_no
        self.tax_no = self.potential_partner_id.tax_no
        self.district = self.potential_partner_id.district
        self.rc = self.potential_partner_id.rc
        self.phone = self.potential_partner_id.phone
        self.mobile = self.potential_partner_id.mobile
        self.city = self.potential_partner_id.city
        self.country_id = self.potential_partner_id.country_id
        self.state_id = self.potential_partner_id.state_id
        self.parent_id = self.potential_partner_id.parent_id
        self.company_type = self.potential_partner_id.company_type
        self.customer_type_id = self.potential_partner_id.customer_type_id
    
    @api.multi
    def button_submit_legal(self):
        self.legal_review = True
        if self.supplier == True:
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_legal_team')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Vendor request '{}' needs a review from the legal team".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        else:
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_legal_team')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "Customer request '{}' needs a review from the legal team".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
    
    @api.multi
    def button_submit_legal_done(self):
        self.legal_review_done = True
        if self.supplier == True:
            subject = "Vendor request {} has been reviewed by the legal team".format(self.name)
            partner_ids = []
            for partner in self.message_partner_ids:
                partner_ids.append(partner.id)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        else:
            subject = "Customer request {} has been reviewed by the legal team".format(self.name)
            partner_ids = []
            for partner in self.message_partner_ids:
                partner_ids.append(partner.id)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    @api.depends('is_company', 'parent_id.commercial_partner_id')
    def _compute_commercial_partner(self):
        return {}
    
    @api.multi
    def send_request_information(self):
        self.write({'state': 'pending_info'})
        config = self.env['mail.template'].sudo().search([('name','=','Request Information')], limit=1)
        mail_obj = self.env['mail.mail']
        if config:
            values = config.generate_email(self.id)
            mail = mail_obj.create(values)
            if mail:
                mail.send()
    
    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return {}
    
    @api.multi
    def button_submit(self):
        if self.supplier == True:
            self.write({'state': 'approve'})
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_one_vendor_approval')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "This Vendor {} needs first approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        else:
            self.write({'state': 'validate'})
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_one_vendor_approval')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "This Customer {} needs approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_validate(self):
        self._check_line_manager()
        self.write({'state': 'validate'})
        if self.supplier == True:
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_two_vendor_approval')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "This Vendor {} needs second approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        else:
            group_id = self.env['ir.model.data'].xmlid_to_object('sunray.group_two_vendor_approval')
            user_ids = []
            partner_ids = []
            for user in group_id.users:
                user_ids.append(user.id)
                partner_ids.append(user.partner_id.id)
            self.message_subscribe(partner_ids=partner_ids)
            subject = "This Customer {} needs second approval".format(self.name)
            self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return {}
    
    @api.multi
    def button_approve(self):
        self.write({'state': 'registered'})
        if self.supplier == True:
            self.vendor_registration = True
            vals = {
                'name' : self.name,
                'company_type' : self.company_type,
                'parent_account_number' : self.parent_account_number,
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
                'email' : self.contact_email,
                'customer': self.customer,
                'supplier' : self.supplier,
                'company' : self.company_id.id,
                'vendor_registration' : self.vendor_registration,
                'completed_vendor_information' : self.completed_vendor_information,
                'report_of_proposers_follow_up' : self.report_of_proposers_follow_up,
                'true_copy_incorporation' : self.true_copy_incorporation,
                'true_copy_memorandum' : self.true_copy_memorandum,
                'sign_and_stamp' : self.Vat_cert,
                'Vat_cert' : self.sign_and_stamp,
                'current_dpr' : self.current_dpr,
                'commercial_certificate' : self.commercial_certificate,
                'proposers_report' : self.proposers_report,
                'copies_of_required_specialist' : self.copies_of_required_specialist,
                'recommendation_letters_from_applicant' : self.recommendation_letters_from_applicant,
                'evidence_of_tax' : self.evidence_of_tax,
                'code_of_conduct' : self.code_of_conduct,
                'specific_references' : self.specific_references,
                'latest_financials' : self.latest_financials,
                'building_no' : self.building_no,
                'office_no' : self.office_no,
                'zip' : self.postal_code,
                'district' : self.district,
                'rc' : self.rc,
                'vat_eligible' : self.vat_eligible,
                'vat_no' : self.vat_no,
                'tax_no' : self.tax_no,
            }
            self.env['res.partner'].create(vals)
        else:
            self.customer_registration = True
            self.customer = True
            if self.potential_partner_id:
                self.potential_partner_id.customer_registration = True
                # self.potential_partner_id.potential_customer = False
                self.potential_partner_id.customer = True
                self.potential_partner_id.name = self.name
                self.potential_partner_id.customer_registration = self.customer_registration
                self.potential_partner_id.company_type = self.company_type
                self.potential_partner_id.parent_account_number = self.parent_account_number
                self.potential_partner_id.image = self.image
                self.potential_partner_id.parent_id = self.parent_id
                self.potential_partner_id.building_no = self.building_no
                self.potential_partner_id.office_no = self.office_no
                self.potential_partner_id.postal_code = self.postal_code
                self.potential_partner_id.vat_no = self.vat_no
                self.potential_partner_id.tax_no = self.tax_no
                self.potential_partner_id.district = self.district
                self.potential_partner_id.rc = self.rc
                self.potential_partner_id.street = self.street
                self.potential_partner_id.street2 = self.street2
                self.potential_partner_id.city = self.city
                self.potential_partner_id.state_id = self.state_id
                self.potential_partner_id.zip = self.zip
                self.potential_partner_id.country_id = self.country_id      
                self.potential_partner_id.vat = self.vat
                self.potential_partner_id.function = self.function
                self.potential_partner_id.phone = self.phone
                self.potential_partner_id.mobile = self.mobile
                self.potential_partner_id.email = self.contact_email
                self.potential_partner_id.supplier = self.supplier
                self.potential_partner_id.company_id = self.company_id
                self.potential_partner_id.completed_customer_information = self.completed_customer_information
                self.potential_partner_id.report_of_proposers_follow_up = self.report_of_proposers_follow_up
                self.potential_partner_id.true_copy_incorporation = self.true_copy_incorporation
                self.potential_partner_id.true_copy_memorandum = self.true_copy_memorandum
                self.potential_partner_id.Vat_cert = self.Vat_cert
                self.potential_partner_id.current_dpr = self.current_dpr
                self.potential_partner_id.commercial_certificate = self.commercial_certificate
                self.potential_partner_id.proposers_report = self.proposers_report
                self.potential_partner_id.recommendation_letters_from_applicant = self.recommendation_letters_from_applicant,
                self.potential_partner_id.evidence_of_tax = self.evidence_of_tax
                self.potential_partner_id.code_of_conduct = self.code_of_conduct
                self.potential_partner_id.latest_financials = self.latest_financials
                self.potential_partner_id.customer_type_id = self.customer_type_id
            else:
                self._check_customer_code()
                vals = {
                    'name' : self.name,
                    'customer_registration' : self.customer_registration,
                    'company_type' : self.company_type,
                    'parent_account_number' : self.parent_account_number,
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
                    'email' : self.contact_email,
                    'customer': self.customer,
                    'supplier' : self.supplier,
                    'company' : self.company_id.id,
                    'completed_customer_information' : self.completed_customer_information,
                    'report_of_proposers_follow_up' : self.report_of_proposers_follow_up,
                    'true_copy_incorporation' : self.true_copy_incorporation,
                    'true_copy_memorandum' : self.true_copy_memorandum,
                    'sign_and_stamp' : self.Vat_cert,
                    'current_dpr' : self.current_dpr,
                    'commercial_certificate' : self.commercial_certificate,
                    'proposers_report' : self.proposers_report,
                    'recommendation_letters_from_applicant' : self.recommendation_letters_from_applicant,
                    'evidence_of_tax' : self.evidence_of_tax,
                    'code_of_conduct' : self.code_of_conduct,
                    'latest_financials' : self.latest_financials,
                    'customer_type_id' : self.customer_type_id,
                }
                self.env['res.partner'].create(vals)
                return {}
    
    @api.multi
    def open_checklist_ticket(self):
        self.ensure_one()
        action = self.env.ref('sunray.sunray_vendor_request_checklist_action').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('name', 'child_of', self.id))
        return action
    
    @api.multi
    def button_reject(self):
        self.write({'state': 'reject'})
        return {}
    
    @api.multi
    def _checklist_count(self):
        oe_checklist = self.env['vendor.internal.approval.checklist']
        for pa in self:
            domain = [('name', '=', pa.id)]
            pres_ids = oe_checklist.search(domain)
            pres = oe_checklist.browse(pres_ids)
            checklist_count = 0
            for pr in pres:
                checklist_count+=1
            pa.checklist_count = checklist_count
        return True



class VendorRequestersReport(models.Model):
    _name = "vendor.requesters.report"
    _description = 'Vendor Requesters Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _get_employee_id(self):
        employee_rec = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id
    
    name = fields.Char(string='Customer Name', required=True)
    code = fields.Char(string='Customer Code', required=True)
    vendor_request_line = fields.One2many(comodel_name='vendor.requesters.report.line', inverse_name='line_id')
    vendor_request_line_two = fields.One2many(comodel_name='vendor.requesters.report.line.two', inverse_name='line_two_id')
    overview = fields.Text(string='Overview of matrial funds Code')    
    requester_name_id = fields.Many2one(comodel_name='hr.employee', string="Requester's name", default=_get_employee_id, required=True) 
    position = fields.Many2one(comodel_name='hr.job', string="Position", related="requester_name_id.job_id") 
    date = fields.Date(string='Date')
    signature = fields.Many2one(comodel_name='res.users', string="Signature") 
    

class VendorRequestersReportLine(models.Model):
    _name = "vendor.requesters.report.line"
    _description = 'Vendor requesters report line 1'
    
    line_id = fields.Many2one(comodel_name='vendor.requesters.report')
    individuals_searched = fields.Char(string='Individuals searched')
    investors_senior_management = fields.Char(string='Investors or senior management?')
    findings = fields.Selection([('none', 'None'), ('yes', 'Yes ')], string='Findings (None/Yes)')
    description = fields.Char(string='Description')


class VendorRequestersReportLineTwo(models.Model):
    _name = "vendor.requesters.report.line.two"
    _description = 'Vendor requesters report line 2'
    
    line_two_id = fields.Many2one(comodel_name='vendor.requesters.report')
    entities_searched = fields.Char(string='Entities searched')
    parent_entities = fields.Char(string='Parent entities or ultimate parent entities?')
    findings = fields.Selection([('none', 'None'), ('yes', 'Yes ')], string='Findings (None/Yes)')
    description = fields.Char(string='Description')


class VendorInternalApprovalChecklist(models.Model):
    _name = "vendor.internal.approval.checklist"
    _description = 'Vendor Internal Approval Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
        
    @api.model
    def _get_default_partner(self):
        ctx = self._context
        if ctx.get('active_model') == 'vendor.request':
            return self.env['vendor.request'].browse(ctx.get('active_ids')[0]).id

    name = fields.Many2one(comodel_name='vendor.request', string='Vendor Request', default=_get_default_partner)
    
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
