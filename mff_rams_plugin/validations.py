from wtforms import validators
from wtforms.validators import ValidationError, StopValidation
from markupsafe import Markup

from .config import c
from uber.badge_funcs import get_real_badge_type
from uber.validations import (ignore_unassigned_and_placeholders, TableInfo, PersonalInfo, OtherInfo, PreregOtherInfo,
                              BadgeExtras, AdminBadgeFlags, CheckInForm, ContactInfo)
from uber.utils import get_age_conf_from_birthday


def country_exclusions(form, field):
    if field.data and field.data in c.EXCLUDED_COUNTRIES:
        raise ValidationError("Midwest FurFest membership, registration, and other MFF-related services are unavailable for your region.")


PersonalInfo.field_validation.validations['country']['exclude'] = country_exclusions
ContactInfo.field_validation.validations['country']['exclude'] = country_exclusions


PersonalInfo.field_validation.required_fields.update({
    'consent_form_email': ("Please enter an email address for us to send consent forms to.",
                           'consent_form_email',
                           lambda x: False and x.form.model.birthdate and x.form.model.age_group_conf['consent_form'])
})


PersonalInfo.field_validation.validations['consent_form_email']['optional'] = validators.Optional()


PersonalInfo.field_validation.validations['badge_printed_name']['length'] = validators.Length(
    max=30, message="Your printed badge name is too long. Please use less than 30 characters.")


@PersonalInfo.field_validation('birthdate')
def attendee_age_checks(form, field):
    age_group_conf = get_age_conf_from_birthday(field.data, c.NOW_OR_AT_CON) \
        if (hasattr(form, "birthdate") and form.birthdate.data) else field.data
    if age_group_conf and not age_group_conf['can_register']:
        raise ValidationError(Markup("At this time Midwest FurFest is not accepting registrations for our Minor attendees \
                                     while we finalize our policies for this year. Please visit our website at \
                                     https://www.furfest.org/attend/register for more information."))


@PersonalInfo.field_validation('onsite_contact')
@ignore_unassigned_and_placeholders
def require_onsite_contact(form, field):
    if not field.data and not form.no_onsite_contact.data and \
            form.model.badge_type not in [c.STAFF_BADGE, c.CONTRACTOR_BADGE] and c.STAFF_RIBBON not in form.model.ribbon_ints:
        raise ValidationError("Please enter contact information for at least one trusted friend onsite, "
                              "or indicate that we should use your emergency contact information instead.")


@PersonalInfo.field_validation('cellphone')
@ignore_unassigned_and_placeholders
def cellphone_required(form, field):
    if not field.data and (not hasattr(form, 'copy_phone') or not form.copy_phone.data
            ) and not form.no_cellphone.data and (
                form.model.is_dealer or form.model.badge_type == c.STAFF_BADGE or c.STAFF_RIBBON in form.model.ribbon_ints):
        raise ValidationError("Please provide a phone number.")


@PersonalInfo.field_validation('cellphone')
def not_same_cellphone_ec(form, field):
    return


OtherInfo.field_validation.required_fields.update({
    'accessibility_requests': ("Please select one or more accessbility accommodations.",
                               'requested_accessibility_services'),
    'other_accessibility_requests': ("Please describe what other accommodations you need.",
                                     'accessibility_requests', lambda x: c.OTHER in x.data),
})


PreregOtherInfo.field_validation.required_fields['group_name'] = (
    "Please confirm your table name.", 'group_name', lambda x: x.form.model.is_dealer)


BadgeExtras.field_validation.required_fields['dietary_restrictions'] = (
    "Please describe your dietary restriction(s).", 'has_restrictions'
)


@BadgeExtras.new_or_changed('attendance_type')
def pit_must_be_adult(form, field):
    if field.data and field.data == c.PARENT_IN_TOW_BADGE and form.model.birthdate and form.model.age_now_or_at_con < 17:
        raise ValidationError(f"{c.BADGES[c.PARENT_IN_TOW_BADGE]} badges must be 17 or older.")


@BadgeExtras.new_or_changed('badge_type')
def badge_upgrade_sold_out(form, field):
    if form.is_admin:
        return

    if field.data == c.SPONSOR_BADGE and not c.SPONSOR_BADGE_AVAILABLE:
        raise ValidationError("Sponsor badges have sold out.")
    elif field.data == c.SHINY_BADGE and not c.SHINY_BADGE_AVAILABLE:
        raise ValidationError("Shiny Sponsor badges have sold out.")


@AdminBadgeFlags.field_validation('badge_num')
def not_in_range(form, field):
    if not field.data or form.no_badge_num and form.no_badge_num.data:
        return

    badge_type = c.STAFF_BADGE if c.STAFF_RIBBON in form.model.ribbon_ints else get_real_badge_type(form.model.badge_type)
    lower_bound, upper_bound = c.BADGE_RANGES[badge_type]
    if not (lower_bound <= int(field.data) <= upper_bound):
        raise ValidationError(f'Badge number {field.data} is out of range for badge type \
                              {c.BADGES[badge_type]} ({lower_bound} - {upper_bound})')


CheckInForm.field_validation.validations['badge_printed_name'].update(PersonalInfo.field_validation.validations['badge_printed_name'])


TableInfo.field_validation.required_fields.update({
    'description': ("Please provide a description for us to evaluate your submission and use in listings.", 'description',
                    lambda x: x.form.model.is_dealer),
    'power_usage': ("Please provide a list of what powered devices you expect to use.", 'power',
                    lambda x: x > 0),
    'location_preference': ("Please select if you would like to be considered for a specific kind of location.",
                            'location_preference', lambda x: x.form.model.is_dealer),
    'adult_content': ("Please tell us if you are selling 18+ content.", 'adult_content',
                      lambda x: x.form.model.is_dealer),
    'ip_issues': ("Please tell us if you have had any IP policy issues in the past.", 'ip_issues',
                  lambda x: x.form.model.is_dealer),
    'ip_issues_text': ("Please tell us how you handled past IP policy issues.", 'ip_issues',
                       lambda x: x == c.YES_ISSUES),
    'agreed_to_dealer_policies': ("You must agree to Midwest Furfest's dealer policies.", 'agreed_to_dealer_policies',
                                  lambda x: x.form.model.is_dealer),
    'agreed_to_ip_policy': ("You must agree to the IP policies for dealers.", 'agreed_to_ip_policy',
                            lambda x: x.form.model.is_dealer),
    'at_con_standby_text': ("Please provide on-site contact info.", 'at_con_standby')
})


TableInfo.field_validation.required_fields.pop('wares', None)


TableInfo.field_validation.validations['power']['range'] = validators.NumberRange(
    max=max(c.DEALER_POWERS.keys()), message="Please select a valid power level.")


TableInfo.field_validation.validations['tax_number']['pattern_match'] = validators.Regexp(
    "^[0-9-]*$", message="Please use only numbers and hyphens for your IBT number.")


TableInfo.field_validation.validations['review_notes']['length'] = validators.Length(
    max=1000, message="Review notes cannot be longer than 1000 characters.")


TableInfo.field_validation.validations['wares']['optional'] = validators.Optional()


TableInfo.field_validation.validations['special_needs']['length'] = validators.Length(
    max=1000, message="Special requests cannot be longer than 1000 characters.")


@TableInfo.new_or_changed('power')
def power_level_required(self, field):
    if not field.form.model.is_dealer:
        return

    if field.data is None or field.data == '' or field.data < 0:
        raise ValidationError("Please select what power level you want, or no power.")


@TableInfo.new_or_changed('table_photo')
def table_photo_is_image(self, field):
    if field.data and field.data.file:
        content_type = field.data.content_type.value
        if not content_type.startswith('image'):
            raise ValidationError(f"Table setup photo ({field.data.filename}) is not a valid image.")


@TableInfo.new_or_changed('table_photo')
def table_photo_size(self, field):
    if field.data and field.data.file:
        field.data.file.seek(0)
        file_size = len(field.data.file.read()) / (1024 * 1024)
        field.data.file.seek(0)
        if file_size > 5:
            raise ValidationError("Please make sure your table setup photo is under 5MB.")