from markupsafe import Markup
from wtforms import (BooleanField, DecimalField, EmailField, Form, FormField,
                     HiddenField, SelectField, SelectMultipleField, IntegerField,
                     StringField, TelField, validators, TextAreaField)
from wtforms.validators import ValidationError, StopValidation
from pockets.autolog import log

from uber.config import c
from uber.forms import AddressForm, CustomValidation, MultiCheckbox, MagForm, IntSelect, SwitchInput, NumberInputGroup, HiddenIntField
from uber.custom_tags import popup_link, format_currency, pluralize, table_prices


@MagForm.form_mixin
class PersonalInfo:
    field_validation, new_or_changed_validation = CustomValidation(), CustomValidation()
    kwarg_overrides = {'badge_printed_name': {'maxlength': 30}}
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
class BadgeExtras:
    new_or_changed_validation = CustomValidation()

    @new_or_changed_validation.badge_type
    def badge_upgrade_sold_out(form, field):
        if field.data == c.SPONSOR_BADGE and not c.SPONSOR_BADGE_AVAILABLE:
            raise ValidationError("Sponsor badges have sold out.")
        elif field.data == c.SHINY_BADGE and not c.SHINY_BADGE_AVAILABLE:
            raise ValidationError("Shiny Sponsor badges have sold out.")

    def badge_type_desc(self):
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
class TableInfo:
    power = IntegerField('Power Level', validators=[
        validators.InputRequired("Please select what power level you want, or no power."),
        validators.NumberRange(min=0, message="Please select what power level you want, or no power."),
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
                descriptions. If your website includes merchandise which may be in violation of our 
                Intellectual Property rules, please confirm that you will not be bringing this merchandise 
                for sale at MFF.""")
    description = StringField('Merchandise Description', validators=[
        validators.DataRequired("Please provide a description for us to evaluate your submission and use in listings.")
        ], description="This will be used both for dealer selection (if necessary) and in all dealer listings.")
    wares = HiddenField('Wares', validators=[validators.Optional()])

    def get_non_admin_locked_fields(self, group):
        locked_fields = self.super_get_non_admin_locked_fields(group)

        if group.is_new:
            return locked_fields

        if group.status in c.DEALER_EDITABLE_STATUSES:
            locked_fields.append('power')
        
        return locked_fields

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