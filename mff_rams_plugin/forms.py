from markupsafe import Markup
from wtforms import (BooleanField, DecimalField, EmailField, Form, FormField,
                     HiddenField, SelectField, SelectMultipleField, IntegerField,
                     StringField, TelField, validators, TextAreaField)
from wtforms.validators import ValidationError, StopValidation
from pockets.autolog import log

from uber.config import c
from uber.forms import AddressForm, MultiCheckbox, MagForm, IntSelect, SwitchInput, DollarInput, HiddenIntField
from uber.custom_tags import popup_link, format_currency, pluralize, table_prices

from uber.config import c

@MagForm.form_mixin
class OtherInfo:
    promo_code = StringField('Registration Code', description="A discount code or an art show agent code.")
    accessibility_requests = SelectMultipleField('Accommodations Desired', choices=c.ACCESSIBILITY_SERVICE_OPTS, coerce=int, validators=[validators.Optional()], widget=MultiCheckbox())
    other_accessibility_requests = StringField('What other accommodations do you need?')
    fursuiting = BooleanField('I plan on fursuiting at the event.', widget=SwitchInput(), description="This is just to help us prepare; it's okay if your plans change!")

    def requested_accessibility_services_label(self):
        return "I have an accessibility request."


@MagForm.form_mixin
class BadgeExtras:
    def badge_printed_name_validators(self, field):
        return (field.validators or []) + [validators.InputRequired("Please enter a name for your custom-printed badge."),
                validators.Length(max=30, message="Your printed badge name is too long. \
                                  Please use less than 30 characters.")]
    
    def badge_printed_name_desc(self):
        return "Badge names have a maximum of 30 characters."

    def badge_type_desc(self):
        return Markup('<span class="popup"><a href="https://www.furfest.org/registration" target="_blank">What are these?</a></span>')


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
        validators.InputRequired("Please provide a description for us to evaluate your submission and use in listings.")
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
    power_fee = IntegerField('Power Fee', widget=DollarInput())