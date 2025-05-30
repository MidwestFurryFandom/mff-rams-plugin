from markupsafe import Markup
from wtforms import (BooleanField, DecimalField, EmailField, Form, FormField,
                     HiddenField, SelectField, SelectMultipleField, IntegerField,
                     StringField, FileField, validators, TextAreaField)
from wtforms.validators import ValidationError, StopValidation
from pockets.autolog import log

from uber.config import c
from uber.forms import TableInfo, CustomValidation, MultiCheckbox, MagForm, IntSelect, SwitchInput, NumberInputGroup, HiddenIntField
from uber.custom_tags import popup_link, format_currency, pluralize, table_prices


@MagForm.form_mixin
class PersonalInfo:
    field_validation, new_or_changed_validation = CustomValidation(), CustomValidation()
    kwarg_overrides = {'badge_printed_name': {'maxlength': 30}} # TODO: Remove
    consent_form_email = EmailField('Email for Consent Forms', validators=[
        validators.DataRequired("Please enter an email address for us to send consent forms to."),
        validators.Length(max=255, message="Email addresses cannot be longer than 255 characters."),
        validators.Email(granular_message=True),
        ],
        description="We will send consent forms to this email address.",
        render_kw={'placeholder': 'test@example.com'})

    def get_optional_fields(self, attendee, is_admin=False):
        optional_list = self.super_get_optional_fields(attendee)

        if c.STAFF_RIBBON in attendee.ribbon_ints and 'onsite_contact' not in optional_list:
            optional_list.append('onsite_contact')
        
        if not attendee.birthdate or not attendee.age_group_conf['consent_form']:
            optional_list.append('consent_form_email')

        return optional_list

    def badge_printed_name_validators(self, field):
        # TODO: Add an upgrade to load_forms later that does this find and replace for you
        return [validator for validator in (field.validators or []) if not isinstance(validator, validators.Length)] + [
            validators.DataRequired("Please enter a name for your custom-printed badge."),
            validators.Length(max=30, message="Your printed badge name is too long. \
                              Please use less than 30 characters.")]
    
    def badge_printed_name_desc(self):
        return "Badge names have a maximum of 30 characters and must not include emoji."
    
    @field_validation.cellphone
    def not_same_cellphone_ec(form, field):
        return

@MagForm.form_mixin
class OtherInfo:
    promo_code = StringField('Registration Code', description="A discount code or an art show agent code.")
    accessibility_requests = SelectMultipleField('Accommodations Desired', validators=[
        validators.DataRequired("Please select one or more accessbility accommodations.")
    ], choices=c.ACCESSIBILITY_SERVICE_OPTS, coerce=int, widget=MultiCheckbox())
    other_accessibility_requests = StringField('What other accommodations do you need?')
    fursuiting = BooleanField('I plan on fursuiting at the event.', widget=SwitchInput(), description="This is just to help us prepare; it's okay if your plans change!")

    def get_optional_fields(self, attendee, is_admin=False):
        optional_list = self.super_get_optional_fields(attendee)
        if not self.requested_accessibility_services.data:
            optional_list.append('accessibility_requests')

        return optional_list
    
    def staffing_desc(self):
        return 

    def requested_accessibility_services_label(self):
        return "I have an accessibility request."
    
    def validate_accessibility_requests(form, field):
        if field.data and c.OTHER in field.data and not form.other_accessibility_requests.data:
            raise ValidationError("Please describe what other accommodations you need.")


@MagForm.form_mixin
class PreregOtherInfo:
    group_name = TableInfo.name

    def group_name_label(self):
        return "Table Name"
    
    def get_optional_fields(self, attendee, is_admin=False):
        optional_list = []
        if not self.requested_accessibility_services.data:
            optional_list.append('accessibility_requests')

        if not attendee.is_dealer:
            optional_list.append('group_name')

        return optional_list


@MagForm.form_mixin
class BadgeExtras:
    field_aliases = {'badge_type': ['badge_type_single']}
    field_validation, new_or_changed_validation = CustomValidation(), CustomValidation()
    attendance_type = HiddenIntField('Single Day or Weekend Badge?')
    badge_type_single = HiddenIntField('Badge Type', default=c.ATTENDEE_BADGE)

    @new_or_changed_validation.badge_type
    def badge_upgrade_sold_out(form, field):
        if field.data == c.SPONSOR_BADGE and not c.SPONSOR_BADGE_AVAILABLE:
            raise ValidationError("Sponsor badges have sold out.")
        elif field.data == c.SHINY_BADGE and not c.SHINY_BADGE_AVAILABLE:
            raise ValidationError("Shiny Sponsor badges have sold out.")

    @field_validation.badge_type_single
    def must_select_day(form, field):
        if form.attendance_type.data and form.attendance_type.data == c.SINGLE_DAY and field.data not in [c.FRIDAY, c.SATURDAY, c.SUNDAY]:
            raise ValidationError("Please select which day you would like to attend.")

    def badge_type_desc(self):
        return Markup('<span class="popup"><a href="https://www.furfest.org/registration" target="_blank"><i class="fa fa-question-circle" aria-hidden="true"></i> Badge details, pickup information, and refund policy</a></span>')
    
    def badge_type_single_desc(self):
        return Markup('<span class="popup"><a href="https://www.furfest.org/registration" target="_blank"><i class="fa fa-question-circle" aria-hidden="true"></i> Badge details, pickup information, and refund policy</a></span>')


@MagForm.form_mixin
class AdminBadgeExtras:
    new_or_changed_validation = CustomValidation()

    @new_or_changed_validation.badge_type
    def badge_upgrade_sold_out(form, field):
        pass # Let admins 'oversell' badges


@MagForm.form_mixin
class BadgeFlags:
    comped_reason = StringField("Reason for Comped Badge")


@MagForm.form_mixin
class Consents:
    def pii_consent_label(self):
        label = "<strong>Yes</strong>, I understand and agree to the data retention policies in {}'s \
            <a href='{}' target='_blank'>privacy policy.</a>".format(c.ORGANIZATION_NAME, c.PRIVACY_POLICY_URL)
        return Markup(label)
    
    def pii_consent_desc(self):
        return ""


@MagForm.form_mixin
class CheckInForm:
    kwarg_overrides = {'badge_printed_name': {'maxlength': 30}}

    # TODO: Overrides should also apply when a form uses another form's field
    def badge_printed_name_validators(self, field):
        return [validator for validator in (field.validators or []) if not isinstance(validator, validators.Length)] + [
            validators.DataRequired("Please enter a name for your custom-printed badge."),
            validators.Length(max=30, message="Your printed badge name is too long. \
                              Please use less than 30 characters.")]


@MagForm.form_mixin
class TableInfo:
    field_validation, new_or_changed_validation = CustomValidation(), CustomValidation()

    power = IntegerField('Power Level', validators=[
        validators.NumberRange(max=max(c.DEALER_POWERS.keys()), message="Please select a valid power level.")
        ], widget=IntSelect())
    power_usage = TextAreaField('Power Usage', description="Please provide a listing of what devices you will be using.")
    tax_number = StringField('Illinois Business Tax Number', validators=[
        validators.Regexp("^[0-9-]*$", message="Please use only numbers and hyphens for your IBT number.")
        ], description="""
                    If you have an Illinois Business license please provide the number here. Note that this 
                    number is in the format 1234-5678; it is not your Federal Tax ID or any other Tax ID number 
                    you may have.""", render_kw={'pattern': "[0-9]{4}-[0-9]{4}", 'title': "1234-5678"})
    review_notes = TextAreaField('Review Notes', validators=[
        validators.Length(max=1000, message="Review notes cannot be longer than 1000 characters.")
    ], description="""
                Please provide any additional information which you feel could assist in our selection process. 
                This could include additional links other than your website or more detailed merchandise 
                descriptions.""")
    description = StringField('Merchandise Description', validators=[
        validators.DataRequired("Please provide a description for us to evaluate your submission and use in listings.")
        ], description="This will be used both for dealer selection (if necessary) and in all dealer listings.")
    wares = HiddenField('Wares', validators=[validators.Optional()])
    social_media = TextAreaField("Social Media Details",
                                 description="Please list any social media accounts you use that should be included in the review process.")
    mff_alumni = BooleanField('I have vended at Midwest FurFest before.')
    art_show_intent = BooleanField('I plan to apply to the Midwest FurFest Art Show.')
    adult_content = SelectField('Selling 18+ Content?', coerce=int, choices=[(0, 'Please select an option')] + c.DEALER_ADULT_OPTS,
                                validators=[validators.DataRequired("Please tell us if you are selling 18+ content.")])
    ip_issues = SelectField('IP Policy History', coerce=int, choices=[(0, 'Please select an option')] + c.DEALER_IP_OPTS,
                            validators=[validators.DataRequired("Please tell us if you have had any IP policy issues in the past.")])
    other_cons = StringField('Other Events',
                             description="Please list any events besides Midwest FurFest that you've vended at before.")
    table_photo = FileField('Table Setup', description='Please upload a photo of your table setup (up to 5MB).', render_kw={'accept': "image/*"})
    shipping_boxes = BooleanField('I plan on or may be shipping boxes or pallets to the convention center.')
    agreed_to_dealer_policies = BooleanField(Markup(f'I have read and agree to the Midwest FurFest policies for dealers.'),
                             validators=[validators.InputRequired("You must agree to Midwest Furfest's dealer policies.")])
    agreed_to_ip_policy = BooleanField(Markup(f'<strong>I have read and agree to the Midwest FurFest IP policies for dealers.</strong>'),
                             validators=[validators.InputRequired("You must agree to the IP policies for dealers.")])
    vehicle_access = BooleanField('I will need vehicle access for load-in.')
    display_height = StringField('Display Height', description="Please provide the estimated display height of your table, in inches.")
    at_con_standby = BooleanField('I will be available on a stand-by basis during the convention.')
    at_con_standby_text = TextAreaField('On-site Contact Info', description="Please provide the quickest way to contact you on-site.",
                                        validators=[validators.DataRequired("Please provide on-site contact info.")])

    def agreed_to_dealer_policies_label(self):
        return Markup(f"""
                      I have read and agree to the <strong><a href="" target="_blank">Midwest FurFest dealer policies</a></strong>.
                      """)

    def agreed_to_ip_policy_label(self):
        return Markup(f"""<strong>
                      I have read and agree to the <a href="" target="_blank">Midwest FurFest IP policies</a> for dealers.
                      </strong>""")

    def get_non_admin_locked_fields(self, group):
        locked_fields = self.super_get_non_admin_locked_fields(group)

        if group.is_new:
            return locked_fields

        if group.status in c.DEALER_EDITABLE_STATUSES:
            locked_fields.append('power')
        
        return locked_fields

    def get_optional_fields(self, attendee, is_admin=False):
        optional_list = self.super_get_optional_fields(attendee)
        if not self.at_con_standby.data:
            optional_list.append('at_con_standby_text')

        return optional_list

    @field_validation.table_photo
    def table_photo_is_image(self, field):
        if field.data and field.data.file:
            content_type = field.data.content_type.value
            if not content_type.startswith('image'):
                raise ValidationError(f"Table setup photo ({field.data.filename}) is not a valid image.")

    @field_validation.table_photo
    def table_photo_size(self, field):
        if field.data and field.data.file:
            field.data.file.seek(0)
            file_size = len(field.data.file.read()) / (1024 * 1024)
            field.data.file.seek(0)
            if file_size > 5:
                raise ValidationError("Please make sure your table setup photo is under 5MB.")

    @new_or_changed_validation.power
    def power_level_required(self, field):
        if field.data is None or field.data == '' or field.data < 0:
            raise ValidationError("Please select what power level you want, or no power.")

    def special_needs_validators(self, field):
        return (field.validators or []) + [
            validators.Length(max=1000, message="Special requests cannot be longer than 1000 characters.")]

    def tables_desc(self):
        return ""
    
    def validate_power_usage(form, field):
        if form.power.data > 0 and not field.data:
            raise ValidationError("Please provide a list of what powered devices you expect to use.")

@MagForm.form_mixin
class AdminTableInfo:
    location = StringField('Table Assignment', render_kw={'placeholder': "Dealer's table location"})
    power_fee = IntegerField('Power Fee', widget=NumberInputGroup())
    socials_checked = BooleanField('Socials Checked')
    table_seen = BooleanField('Table Setup Seen')
    ip_concerns = TextAreaField('IP Concerns')
    other_concerns = TextAreaField('Other Concerns')

@MagForm.form_mixin
class ArtistMarketplaceForm:
    def terms_accepted_label(self):
        return Markup("I have read both the <a href='https://www.furfest.org/vendors/menagerie/rules' target='_blank'>general rules</a> "
                      " for the artist alley and marketplace and the <a href='https://www.furfest.org/vendors/menagerie/marketplace' target='_blank'>"
                      f"specific rules</a> for the artist marketplace and understand the requirements, including the ${c.ARTIST_MARKETPLACE_FEE} fee.")