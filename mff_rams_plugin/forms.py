from markupsafe import Markup
from wtforms import BooleanField, SelectMultipleField, StringField, validators

from uber.forms import MagForm, MultiCheckbox, SwitchInput

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