from uber.automated_emails import ArtShowAppEmailFixture, AutomatedEmailFixture, MarketplaceEmailFixture, StopsEmailFixture
from uber.config import c
from uber.models import AttendeeAccount
from uber.utils import before, days_before


MarketplaceEmailFixture(
    'Your {EVENT_NAME} ({EVENT_DATE}) Dealer registration is due in one week',
    'dealers/payment_reminder.txt',
    lambda g: g.status == c.APPROVED and days_before(7, g.dealer_payment_due, 2)() and g.is_unpaid,
    needs_approval=False,
    ident='dealer_reg_payment_reminder_due_soon_mff')

MarketplaceEmailFixture(
    'Last chance to pay for your {EVENT_NAME} ({EVENT_DATE}) Dealer registration',
    'dealers/payment_reminder.txt',
    lambda g: g.status == c.APPROVED and days_before(2, g.dealer_payment_due)() and g.is_unpaid,
    needs_approval=False,
    ident='dealer_reg_payment_reminder_last_chance_mff')

MarketplaceEmailFixture(
    'Your {EVENT_NAME} ({EVENT_DATE}) dealer application has been waitlisted',
    'dealers/pending_waitlisted.txt',
    lambda g: g.status == c.WAITLISTED and g.registered < c.DEALER_REG_DEADLINE,
    when=before(c.DEALER_WAITLIST_CLOSED),
    ident='dealer_pending_now_waitlisted_mff')

ArtShowAppEmailFixture(
    '{EVENT_NAME} Charity Donations needed',
    'art_show/charity.txt',
    lambda a: a.status == c.APPROVED,
    when=before(c.ART_SHOW_CHARITY_DEADLINE),
    ident='art_show_charity')

StopsEmailFixture(
    'Volunteering At {EVENT_NAME}!',
    'volunteer_interest.html',
    lambda a: c.VOLUNTEER_RIBBON in a.ribbon_ints,
    ident='volunteer_interest')

AutomatedEmailFixture(
    AttendeeAccount,
    '{EVENT_NAME} Hotel Lottery Instructions',
    'hotel_lottery/instructions.html',
    lambda aa: aa.hotel_eligible_attendees,
    ident='hotel_lottery_instructions')