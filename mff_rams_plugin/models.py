import math
from datetime import timedelta

from residue import CoerceUTF8 as UnicodeText
from pockets import cached_classproperty
from sqlalchemy import and_, or_
from sqlalchemy.types import Integer
from sqlalchemy.ext.hybrid import hybrid_property

from uber.models import Session
from uber.config import c
from uber.utils import add_opt, localized_now, localize_datetime, remove_opt
from uber.models.types import Choice, DefaultColumn as Column, MultiChoice
from uber.decorators import presave_adjustment


@Session.model_mixin
class SessionMixin:
    def all_panelists(self):
        return self.query(Attendee).filter(or_(
            Attendee.ribbon.contains(c.PANELIST_RIBBON),
            Attendee.ribbon == c.STAFF_RIBBON,
            Attendee.badge_type == c.GUEST_BADGE))\
            .order_by(Attendee.full_name).all()


@Session.model_mixin
class Group:
    power = Column(Choice(c.DEALER_POWER_OPTS), default=0)
    power_fee = Column(Integer, default=0)
    power_usage = Column(UnicodeText)
    location = Column(UnicodeText, default='', admin_only=True)
    table_fee = Column(Integer, default=0)
    tax_number = Column(UnicodeText)
    review_notes = Column(UnicodeText)

    @cached_classproperty
    def import_fields(cls):
        return ['power', 'power_fee', 'power_usage', 'tax_number', 'review_notes']

    @presave_adjustment
    def guest_groups_approved(self):
        if self.leader and self.leader.badge_type == c.GUEST_BADGE and self.status == c.UNAPPROVED:
            self.status = c.APPROVED

    @presave_adjustment
    def set_power_fee(self):
        if self.auto_recalc:
            self.power_fee = self.default_power_fee or self.power_fee

        if self.power_fee == None:
            self.power_fee = 0

    @presave_adjustment
    def float_table_to_int(self):
        # Fix some data weirdness with prior year groups
        self.tables = int(self.tables)

    @property
    def default_power_fee(self):
        return c.POWER_PRICES.get(int(self.power), None)

    @property
    def dealer_payment_due(self):
        if self.approved:
            return self.approved + timedelta(c.DEALER_PAYMENT_DAYS)

    @property
    def dealer_payment_is_late(self):
        if self.approved:
            return localized_now() > localize_datetime(self.dealer_payment_due)

    @presave_adjustment
    def dealers_add_badges(self):
        if self.is_dealer and self.is_new:
            self.can_add = True

    @property
    def tables_repr(self):
        return c.TABLE_OPTS[int(self.tables) - 1][1] if self.tables \
            else "No Table"

    @property
    def dealer_max_badges(self):
        return c.MAX_DEALERS or min(math.ceil(self.tables) * 3, 12)

    def calc_group_price_change(self, **kwargs):
        preview_group = Group(**self.to_dict())
        current_cost = int(self.cost * 100)
        new_cost = None

        if 'cost' in kwargs:
            try:
                preview_group.cost = int(kwargs['cost'])
            except TypeError:
                preview_group.cost = 0
            new_cost = preview_group.cost * 100
        if 'power_fee' in kwargs:
            try:
                preview_group.power_fee = int(kwargs['power_fee'])
            except TypeError:
                preview_group.power_fee = 0
            return self.power_fee * 100, (preview_group.power_fee * 100) - (self.power_fee * 100)
        if 'power' in kwargs:
            preview_group.power = int(kwargs['power'])
            if preview_group.default_power_fee is not None:
                new_power_fee = int(preview_group.default_power_fee)
                return self.power_fee * 100, (new_power_fee * 100) - (self.power_fee * 100)
            elif preview_group.default_power_fee == 0:
                return self.power_fee * 100, self.power_fee * 100 * -1
            else:
                # We changed the power option but that didn't actually change their power fee
                return 0, 0
        if 'tables' in kwargs:
            preview_group.tables = int(kwargs['tables'])
            return self.default_table_cost * 100, (preview_group.default_table_cost * 100) - (self.default_table_cost * 100)
        if 'badges' in kwargs:
            num_new_badges = int(kwargs['badges']) - self.badges_purchased
            return self.current_badge_cost * 100, self.new_badge_cost * num_new_badges * 100

        if not new_cost:
            new_cost = int(preview_group.default_cost * 100)
        return current_cost, new_cost - current_cost


@Session.model_mixin
class MarketplaceApplication:
    MATCHING_DEALER_FIELDS = ['categories', 'categories_text', 'description', 'special_needs', 'tax_number']

    tax_number = Column(UnicodeText)


@Session.model_mixin
class Attendee:
    comped_reason = Column(UnicodeText, default='', admin_only=True)
    fursuiting = Column(Choice(c.FURSUITING_OPTS), nullable=True)
    accessibility_requests = Column(MultiChoice(c.ACCESSIBILITY_SERVICE_OPTS))
    other_accessibility_requests = Column(UnicodeText)

    @cached_classproperty
    def import_fields(cls):
        return ['comped_reason', 'fursuiting']

    @presave_adjustment
    def save_group_cost(self):
        if self.group and self.group.auto_recalc:
            self.group.cost = self.group.default_cost

    @presave_adjustment
    def never_spam(self):
        self.can_spam = False

    @presave_adjustment
    def not_attending_need_not_pay(self):
        if self.badge_status == c.NOT_ATTENDING:
            self.paid = c.NEED_NOT_PAY
            self.comped_reason = "Automated: Not Attending badge status."

    @presave_adjustment
    def staffing_badge_and_ribbon_adjustments(self):
        if self.badge_type == c.STAFF_BADGE or c.STAFF_RIBBON in self.ribbon_ints:
            self.ribbon = remove_opt(self.ribbon_ints, c.VOLUNTEER_RIBBON)

        elif self.staffing and self.badge_type != c.STAFF_BADGE \
                and c.STAFF_RIBBON not in self.ribbon_ints and c.VOLUNTEER_RIBBON not in self.ribbon_ints:
            self.ribbon = add_opt(self.ribbon_ints, c.VOLUNTEER_RIBBON)

        if self.badge_type == c.STAFF_BADGE or c.STAFF_RIBBON in self.ribbon_ints:
            self.staffing = True
            if not self.overridden_price and self.paid in [c.NOT_PAID, c.PAID_BY_GROUP]:
                self.paid = c.NEED_NOT_PAY

        if self.badge_num and self.badge_num in range(c.BADGE_RANGES[c.STAFF_BADGE][0],
                                                      c.BADGE_RANGES[c.STAFF_BADGE][1]
                                                ) and self.badge_status == c.IMPORTED_STATUS and self.badge_type != c.STAFF_BADGE:
            self.ribbon = add_opt(self.ribbon_ints, c.STAFF_RIBBON)

    def undo_extras(self):
        if self.active_receipt:
            return "Could not undo extras, this attendee has an open receipt!"
        self.amount_extra = 0
        self.extra_donation = 0
        if self.badge_type in c.BADGE_TYPE_PRICES:
            if c.STAFF_RIBBON in self.ribbon_ints:
                self.badge_type = c.STAFF_BADGE
            else:
                self.badge_type = c.ATTENDEE_BADGE

    @property
    def ribbon_and_or_badge(self):
        ribbon_labels = self.ribbon_labels
        if self.badge_type == c.STAFF_BADGE and c.STAFF_RIBBON in self.ribbon_ints:
            ribbon_labels.remove(c.RIBBONS[c.STAFF_RIBBON])
        if self.ribbon and self.badge_type != c.ATTENDEE_BADGE:
            return ' / '.join([self.badge_type_label] + ribbon_labels)
        elif self.ribbon:
            return ' / '.join(ribbon_labels)
        else:
            return self.badge_type_label

    @property
    def age_discount(self):
        if 'val' in self.age_group_conf \
                and self.age_group_conf['val'] == c.UNDER_13 \
                and c.AT_THE_CON:
            if self.badge_type == c.ATTENDEE_BADGE:
                discount = 35
            elif self.badge_type in [c.FRIDAY, c.SUNDAY]:
                discount = 15
            elif self.badge_type == c.SATURDAY:
                discount = 20
            return -discount
        return -self.age_group_conf['discount']

    @property
    def paid_for_a_shirt(self):
        return self.badge_type in [c.SPONSOR_BADGE, c.SHINY_BADGE]

    @property
    def staffing_or_will_be(self):
        return self.staffing or self.badge_type == c.STAFF_BADGE \
               or c.VOLUNTEER_RIBBON in self.ribbon_ints or c.STAFF_RIBBON in self.ribbon_ints

    @property
    def merch_items(self):
        """
        Here is the business logic surrounding shirts:
        - People who kick in enough to get a shirt get an event shirt.
        - People with staff badges get a configurable number of staff shirts.
        - Volunteers who meet the requirements get a complementary event shirt
            (NOT a staff shirt).

        If the c.SEPARATE_STAFF_SWAG setting is true, then this excludes staff
        merch; see the staff_merch property.

        This property returns a list containing strings and sub-lists of each
        donation tier with multiple sub-items, e.g.
            [
                'tshirt',
                'Supporter Pack',
                [
                    'Swag Bag',
                    'Badge Holder'
                ],
                'Season Pass Certificate'
            ]
        """
        merch = []
        for amount, desc in sorted(c.DONATION_TIERS.items()):
            if amount and self.amount_extra >= amount:
                merch.append(desc)
                items = c.DONATION_TIER_ITEMS.get(amount, [])
                if len(items) == 1:
                    merch[-1] = items[0]
                elif len(items) > 1:
                    merch.append(items)

        if self.num_event_shirts_owed == 1 and not self.paid_for_a_shirt:
            merch.append('A T-shirt')
        elif self.num_event_shirts_owed > 1:
            merch.append('A 2nd T-Shirt')

        if merch and self.volunteer_event_shirt_eligible and not self.volunteer_event_shirt_earned:
            merch[-1] += (
                ' (this volunteer must work at least {} hours or they will be reported for picking up their shirt)'
                .format(c.HOURS_FOR_SHIRT))
        
        if self.badge_type == c.SPONSOR_BADGE:
            merch.append('Sponsor merch')
        if self.badge_type == c.SHINY_BADGE:
            merch.append('Shiny Sponsor merch')

        if not c.SEPARATE_STAFF_MERCH:
            merch.extend(self.staff_merch_items)

        if self.extra_merch:
            merch.append(self.extra_merch)

        return merch
