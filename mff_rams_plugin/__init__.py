from os.path import join

from uber.jinja import template_overrides
from uber.utils import mount_site_sections, static_overrides
from .config import config
from . import forms  # noqa: F401
from . import models  # noqa: F401
from . import model_checks  # noqa: F401
from . import automated_emails  # noqa: F401
from . import receipt_items  # noqa: F401
from .tasks import *  # noqa: F401,E402,F403
from .validations import *  # noqa: F401,E402,F403


static_overrides(join(config['module_root'], 'static'))
template_overrides(join(config['module_root'], 'templates'))
mount_site_sections(config['module_root'])


from uber.payments import PreregCart
old_prereg_cart_checks = PreregCart.prereg_cart_checks


def prereg_cart_checks(self, session):
    error = old_prereg_cart_checks(self, session)
    if error:
        return error

    account = session.current_attendee_account()
    for attendee in self.attendees:
        if attendee.badge_type == c.PARENT_IN_TOW_BADGE:
            paid_minors_in_cart = any([a for a in self.attendees if a.birthdate and a.age_now_or_at_con < c.ACCOMPANYING_ADULT_AGE \
                                       and a.total_cost_if_valid])
            if not account.pit_eligible and not paid_minors_in_cart:
                return "You cannot register an Accompanying Adult badge when you have no paid badges under 18 years old."


PreregCart.prereg_cart_checks = prereg_cart_checks