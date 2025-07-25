from markupsafe import Markup
from wtforms import (BooleanField, DecimalField, EmailField, Form, FormField,
                     HiddenField, SelectField, SelectMultipleField, IntegerField,
                     StringField, FileField, TextAreaField)
from pockets.autolog import log

from uber.config import c
from uber.forms import TableInfo, CustomValidation, MultiCheckbox, MagForm, IntSelect, SwitchInput, NumberInputGroup, HiddenIntField
from uber.custom_tags import popup_link, format_currency, pluralize, table_prices


@MagForm.form_mixin
class PersonalInfo:
    consent_form_email = EmailField('Email for Consent Forms', 
                                    description="We will send consent forms to this email address.",
                                    render_kw={'placeholder': 'test@example.com'})

    def badge_printed_name_desc(self):
        return "Badge names have a maximum of 30 characters and must not include emoji."


@MagForm.form_mixin
class OtherInfo:
    promo_code = StringField('Registration Code', description="A discount code or an art show agent code.")
    accessibility_requests = SelectMultipleField('Accommodations Desired',
                                                 choices=c.ACCESSIBILITY_SERVICE_OPTS, coerce=int, widget=MultiCheckbox())
    other_accessibility_requests = StringField('What other accommodations do you need?')
    fursuiting = BooleanField('I plan on fursuiting at the event.', widget=SwitchInput(), description="This is just to help us prepare; it's okay if your plans change!")

    def staffing_desc(self):
        return ""

    def requested_accessibility_services_label(self):
        return "I have an accessibility request."


@MagForm.form_mixin
class PreregOtherInfo:
    group_name = TableInfo.name

    def group_name_label(self):
        return "Table Name"


@MagForm.form_mixin
class StaffingInfo:
    def staffing_desc(self):
        return ""


@MagForm.form_mixin
class BadgeExtras:
    field_aliases = {'badge_type': ['badge_type_single']}
    field_validation, new_or_changed_validation = CustomValidation(), CustomValidation()
    has_restrictions = BooleanField("I have a dietary restriction that needs accommodating for convention-sponsored meals.")
    dietary_restrictions = StringField("Dietary Restriction(s)")

    def badge_type_desc(self):
        return Markup('<span class="popup"><a href="https://www.furfest.org/registration" target="_blank"><i class="fa fa-question-circle" aria-hidden="true"></i> Badge details, pickup information, and refund policy</a></span>')
    
    def badge_type_single_desc(self):
        return Markup('<span class="popup"><a href="https://www.furfest.org/registration" target="_blank"><i class="fa fa-question-circle" aria-hidden="true"></i> Badge details, pickup information, and refund policy</a></span>')


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
    power = IntegerField('Power Level', widget=IntSelect(), description="Final cost for power is subject to change.")
    power_usage = TextAreaField('Power Usage', description="Please provide a listing of what devices you will be using.")
    location_preference = SelectField('Location Preference', default=0, coerce=int,
                                      choices=[(0, 'Please select an option')] + c.DEALER_LOCATION_PREFERENCE_OPTS,
                                      description="If you are selected for an endcap, you will be charged an additional $150 fee.")
    tax_number = StringField('Illinois Business Tax Number', description="""
                             If you have an Illinois Business license please provide the number here. Note that this 
                             number is in the format 1234-5678; it is not your Federal Tax ID or any other Tax ID number 
                             you may have.""", render_kw={'pattern': "[0-9]{4}-[0-9]{4}", 'title': "1234-5678"})
    review_notes = TextAreaField('Review Notes', description="""
                                 Please provide any additional information which you feel could assist in our selection process. 
                                 This could include additional links other than your website or more detailed merchandise 
                                 descriptions.""")
    description = StringField('Merchandise Description',
                              description="This will be used both for dealer selection (if necessary) and in all dealer listings.")
    social_media = TextAreaField("Social Media Details",
                                 description="Please list any social media accounts you use that should be included in the review process. Applications without any social media accounts listed are less likely to be considered.")
    mff_alumni = BooleanField('I have vended at Midwest FurFest before.')
    art_show_intent = BooleanField('I plan to apply to the Midwest FurFest Art Show.')
    adult_content = SelectField('Selling 18+ Content?', coerce=int, choices=[(0, 'Please select an option')] + c.DEALER_ADULT_OPTS)
    ip_issues = SelectField('IP Policy History', coerce=int, choices=[(0, 'Please select an option')] + c.DEALER_IP_OPTS,
                            description="If yes, please tell us how it was handled. We are simply looking for honesty here, \
                                and this does not count against your application, but rather a chance to display integrity and growth. ")
    ip_issues_text = StringField('How did you handle past IP issues?')
    other_cons = StringField(f'Other Conventions in {c.EVENT_YEAR}',
                             description=f"Please list any events that you've vended at within {c.EVENT_YEAR}.")
    table_photo = FileField('Table Setup', render_kw={'accept': "image/*"})
    shipping_boxes = BooleanField('I plan on or may be shipping boxes or pallets to the convention center.')
    agreed_to_dealer_policies = BooleanField(Markup(f'I have read and agree to the Midwest FurFest policies for dealers.'))
    agreed_to_ip_policy = BooleanField(Markup(f'<strong>I have read and agree to the Midwest FurFest IP policies for dealers.</strong>'))
    vehicle_access = BooleanField('I will need vehicle access for load-in.')
    display_height = StringField('Display Height')
    at_con_standby = BooleanField('Please add me to the on site stand-by list if my application is waitlisted. \
                                  I will be available to be contacted if a spot becomes available on short term notice at the convention.')
    at_con_standby_text = TextAreaField('On-site Contact Info',
                                        description="Please provide the quickest way to contact you on-site.")

    def agreed_to_dealer_policies_label(self):
        return Markup(f"""
                      I have read and agree to the <strong><a href="" target="_blank">Midwest FurFest dealer policies</a></strong>.
                      """)

    def agreed_to_ip_policy_label(self):
        return Markup(f"""<strong>
                      I have read and agree to the <a href="" target="_blank">Midwest FurFest IP policies</a> for dealers.
                      </strong>""")
    
    def display_height_desc(self):
        return Markup(f"""Estimated height of your entire Dealer Display (including all signage) from floor to top.
                      <br/>Please be sure to read our new guidelines on display height limitations in the
                      <a href="https://www.furfest.org/vendors/dealers/information" target="_blank">Dealers Agreement</a>.""")
    
    def table_photo_desc(self):
        return Markup(f"""Please upload a photo of what your Dealer Display looks like, from within the past year,
                      so we can get to know you and what you want to sell.
                      <br/>*IP items are OK in the photo as long as you tell us you won't be selling them at our event.
                      Please see the <a href="https://www.furfest.org/vendors/dealers/information" target="_blank">Dealers 
                      Agreement</a> for more info on our IP policies.""")

    def get_non_admin_locked_fields(self, group):
        locked_fields = self.super_get_non_admin_locked_fields(group)

        if group.is_new:
            return locked_fields

        if group.status in c.DEALER_EDITABLE_STATUSES:
            locked_fields.append('power')
        
        return locked_fields

    def tables_desc(self):
        return ""


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