from uber.automated_emails import ArtShowAppEmailFixture, AutomatedEmailFixture, MarketplaceEmailFixture, StopsEmailFixture
from uber.config import c
from uber.models import Attendee, AttendeeAccount, AutomatedEmail, LotteryApplication
from uber.utils import before, days_before, days_after


AutomatedEmailFixture(
    Attendee,
    'A Message from Furfest Accessibility Services',
    'accessibility_info.html',
    "lambda a: a.requested_accessibility_services",
    'accessibility_info',
    when=[days_before(7, c.EPOCH)],
    sender='accessibility@furfest.org'
)


AutomatedEmailFixture(
    Attendee,
    f'{c.EVENT_NAME} registration confirmed',
    'reg_workflow/attendee_confirmation.html',
    "lambda a: not a.placeholder and a.badge_type in [c.PARENT_IN_TOW_BADGE, c.KID_IN_TOW_BADGE]",
    'kitpit_badge_confirmed',
    allow_at_the_con=True)


if c.DEALER_PAYMENT_DUE:
    MarketplaceEmailFixture(
            'Payment Now Due for your Midwest FurFest Dealer Group and Registrations',
            'dealers/payment_ready.txt',
            "lambda g: g.status in c.DEALER_ACCEPTED_STATUSES and days_after(30, g.approved)() and g.is_unpaid",
            'dealer_reg_payment_reminder')


    MarketplaceEmailFixture(
        f'Your {c.EVENT_NAME} ({c.EVENT_DATE}) Dealer registration is due in one week',
        'dealers/payment_reminder.txt',
        "lambda g: g.status in [c.APPROVED, c.SHARED] and days_before(7, g.dealer_payment_due, 2)() and g.is_unpaid",
        'dealer_reg_payment_reminder_due_soon')


    MarketplaceEmailFixture(
        f'Last chance to pay for your {c.EVENT_NAME} ({c.EVENT_DATE}) Dealer registration',
        'dealers/payment_reminder_final.txt',
        "lambda g: g.status in [c.APPROVED, c.SHARED] and days_before(2, g.dealer_payment_due)() and g.is_unpaid",
        'dealer_reg_payment_reminder_last_chance')


AutomatedEmailFixture(
        Attendee,
        f'{c.EVENT_NAME} Dealers Waitlist Has Ended',
        'dealers/badge_converted.html', None,
        'dealer_waitlist_exhausted',
        sender=c.MARKETPLACE_EMAIL,
    )

ArtShowAppEmailFixture(
    f'{c.EVENT_NAME} Charity Donations needed',
    'art_show/charity.txt',
    "lambda a: a.status == c.APPROVED",
    'art_show_charity',
    when=[before(c.ART_SHOW_CHARITY_DEADLINE)])

StopsEmailFixture(
    f'Volunteering At {c.EVENT_NAME}!',
    'volunteer_interest.html',
    "lambda a: c.VOLUNTEER_RIBBON in a.ribbon_ints",
    'volunteer_interest')

StopsEmailFixture(
    f'{c.EVENT_NAME} Volunteering Update!',
    'volunteer_update.html',
    "lambda a: c.VOLUNTEER_RIBBON in a.ribbon_ints",
    'volunteer_update')

AutomatedEmailFixture(
    LotteryApplication,
    f'Information Needed for {c.EVENT_NAME} Hotel Lottery',
    'hotel_lottery/lottery_phone.html',
    "lambda a: a.cellphone == '' and a.attendee and a.attendee.cellphone == '' and a.status == c.COMPLETE and a.current_step == (a.last_step - 5) and a.entry_type != c.GROUP_ENTRY",
    'lottery_phone',
    sender=c.HOTEL_LOTTERY_EMAIL,
)

AutomatedEmailFixture(
    AttendeeAccount,
    f'{c.EVENT_NAME} Hotel Lottery Instructions',
    'hotel_lottery/instructions.html',
    "lambda aa: aa.hotel_eligible_staff and c.AFTER_HOTEL_LOTTERY_STAFF_START or aa.hotel_eligible_attendees and c.AFTER_HOTEL_LOTTERY_FORM_START",
    'hotel_lottery_instructions',
    sender=c.HOTEL_LOTTERY_EMAIL)