from markupsafe import Markup
from wtforms import (BooleanField, DecimalField, EmailField, Form, FormField,
                     HiddenField, SelectField, SelectMultipleField, IntegerField,
                     StringField, TelField, validators, TextAreaField)
from wtforms.validators import ValidationError, StopValidation

from uber.config import c
from uber.forms import AddressForm, MultiCheckbox, MagForm, IntSelect, SwitchInput, DollarInput, HiddenIntField
from uber.custom_tags import popup_link, format_currency, pluralize, table_prices
from uber.validations import attendee as attendee_validators

from uber.config import c

@MagForm.form_mixin
class OtherInfo:
    accessibility_requests = SelectMultipleField('Accommodations Desired', choices=c.ACCESSIBILITY_SERVICE_OPTS, coerce=int, validators=[validators.Optional()], widget=MultiCheckbox())
    other_accessibility_requests = StringField('What other accommodations do you need?')
    fursuiting = BooleanField('I plan on fursuiting at the event.', widget=SwitchInput(), description="This is just to help us prepare; it's okay if your plans change!")

    def requested_accessibility_services_label(self):
        return "I have an accessibility request."

@MagForm.form_mixin
class Consents:
    def pii_consent_label(self):
        label = "<strong>Yes</strong>, I understand and agree that {ORGANIZATION_NAME} will store the personal information I provided above for the limited purposes of contacting me about my registration"
        label += ', accessibility needs, fursuiting plans, or volunteer opportunities selected at sign-up.'
        return Markup(label)
    

@MagForm.form_mixin
class TableInfo:
    power = IntegerField('Power Level', validators=[
        validators.InputRequired("Please select what power level you want, or no power.")
        ], widget=IntSelect())
    power_usage = TextAreaField('Power Usage', description="Please provide a listing of what devices you will be using.")
    tax_number = StringField('Illinois Business Tax Number',
                             description="""
                             If you have an Illinois Business license please provide the number here. Note that this 
                             number is in the format 1234-5678; it is not your Federal Tax ID or any other Tax ID number 
                             you may have.""",
                            render_kw={'pattern': "[0-9]{4}-[0-9]{4}", 'title': "1234-5678"})
    review_notes = TextAreaField('Review Notes',
                                 description="""
                                 Please provide any additional information which you feel could assist in our selection process. 
                                 This could include additional links other than your website or more detailed merchandise 
                                 descriptions. If your website includes merchandise which may be in violation of our 
                                 Intellectual Property rules, please confirm that you will not be bringing this merchandise 
                                 for sale at MFF.""")
    description = StringField('Merchandise Description', validators=[
        validators.InputRequired("Please provide a description for us to evaluate your submission and use in listings.")
        ], description="This will be used both for dealer selection (if necessary) and in all dealer listings.")
    wares = HiddenField('Wares', validators=[validators.Optional()])

    def tables_desc(self):
        return ""
