from collections import defaultdict
from pockets.autolog import log
from sqlalchemy import func
from sqlalchemy.sql.expression import literal

from uber.config import c
from uber.decorators import all_renderable, csv_file
from uber.models import Attendee, Group
from uber.utils import localized_now


class RegistrationDataOneYear:
    def __init__(self):
        self.event_name = ""

        # what is the final day of this event (i.e. Sunday of a Fri->Sun festival)
        self.end_date = ""

        # this holds how many registrations were taken each day starting at 365 days from the end date of the event.
        # this array is in chronological order and does not skip days.
        #
        # examples:
        # registrations_per_day[0]   is the #regs that were taken on end_date-365 (1 year before the event)
        # .....
        # registrations_per_day[362] is the #regs that were taken on end_date-2 (2 days before the end date)
        # registrations_per_day[363] is the #regs that were taken on end_date-1 (the day before the end date)
        # registrations_per_day[364] is the #regs that were taken on end_date
        self.registrations_per_day = []

        # same as above, but, contains a cumulative sum of the same data
        self.registrations_per_day_cumulative_sum = []

        self.num_days_to_report = 365

    def query_current_year(self, session):
        self.event_name = c.EVENT_NAME_AND_YEAR

        # TODO: we're hacking the timezone info out of ESCHATON (final day of event). probably not the right thing to do
        self.end_date = c.DATES['ESCHATON'].replace(hour=0, minute=0,
                                                    second=0,
                                                    microsecond=0,
                                                    tzinfo=None)

        # return registrations where people actually paid money
        # exclude: dealers
        reg_per_day = session.query(
            func.date_trunc(literal('day'), Attendee.registered),
            func.count(
                func.date_trunc(literal('day'), Attendee.registered))
        ) \
            .outerjoin(Attendee.group) \
            .filter(
            (
                (Attendee.paid == c.PAID_BY_GROUP) &  # if they're paid by group
                (Group.amount_paid >= Group.cost * 100)  # make sure they've paid something, or are comped
            ) | (  # OR
                (Attendee.badge_status == c.COMPLETED_STATUS)
                # if they're an attendee, make sure they're check-in-able
            )
        ) \
            .group_by(func.date_trunc(literal('day'), Attendee.registered)) \
            .order_by(func.date_trunc(literal('day'), Attendee.registered)) \
            .all()  # noqa: E711

        # now, convert the query's data into the format we need.
        # SQL will skip days without registrations
        # we need all self.num_days_to_report days to have data, even if it's zero

        # create 365 elements in the final array
        self.registrations_per_day = self.num_days_to_report * [0]

        for reg_data in reg_per_day:
            day = reg_data[0]
            reg_count = reg_data[1]

            day_offset = self.num_days_to_report - (
                self.end_date - day).days
            day_index = day_offset - 1

            if day_index < 0 or day_index >= self.num_days_to_report:
                log.info(
                    "Ignoring some analytics data because it's not in range of the year before c.ESCHATON. "
                    "Either c.ESCHATON is set incorrectly or you have registrations starting 1 year before ESCHATON, "
                    "or occuring after ESCHATON. day_index=" + str(
                        day_index))
                continue

            self.registrations_per_day[day_index] = reg_count

        self.compute_cumulative_sum_from_registrations_per_day()

    # compute cumulative sum up until the last non-zero data point
    def compute_cumulative_sum_from_registrations_per_day(self):

        if len(self.registrations_per_day) != self.num_days_to_report:
            raise 'array validation error: array size should be the same as the report size'

        # figure out where the last non-zero data point is in the array
        last_useful_data_index = self.num_days_to_report - 1
        for regs in reversed(self.registrations_per_day):
            if regs != 0:
                break  # found it, so we're done.
            last_useful_data_index -= 1

        # compute the cumulative sum, leaving all numbers past the last data point at zero
        self.registrations_per_day_cumulative_sum = self.num_days_to_report * [
            0]
        total_so_far = 0
        current_index = 0
        for regs_this_day in self.registrations_per_day:
            total_so_far += regs_this_day
            self.registrations_per_day_cumulative_sum[
                current_index] = total_so_far
            if current_index == last_useful_data_index:
                break
            current_index += 1

    def dump_data(self):
        return {
            "registrations_per_day": self.registrations_per_day,
            "registrations_per_day_cumulative_sum": self.registrations_per_day_cumulative_sum,
            "event_name": self.event_name,
            "event_end_date": self.end_date.strftime("%d-%m-%Y"),
        }

@all_renderable()
class Root:
    def index(self, session):
        pass

    def comped_badges(self, session, message='', show='all'):
        all_comped = session.valid_attendees()\
            .filter(Attendee.paid == c.NEED_NOT_PAY)
        claimed_comped = all_comped.filter(Attendee.placeholder == False)
        unclaimed_comped = all_comped.filter(Attendee.placeholder == True)
        if show == 'claimed':
            comped_attendees = claimed_comped
        elif show == 'unclaimed':
            comped_attendees = unclaimed_comped
        else:
            comped_attendees = all_comped

        return {
            'message': message,
            'comped_attendees': comped_attendees,
            'all_comped': all_comped.count(),
            'claimed_comped': claimed_comped.count(),
            'unclaimed_comped': unclaimed_comped.count(),
            'show': show
        }

    def sponsors_counts(self, session):
        sponsors = session.query(Attendee).filter(Attendee.badge_type == c.SPONSOR_BADGE)
        shiny_sponsors = session.query(Attendee).filter(Attendee.badge_type == c.SHINY_BADGE)
        sponsor_counts = {}
        shiny_counts = {}

        for val, desc in c.BADGE_STATUS_OPTS:
            sponsor_counts[desc] = sponsors.filter(Attendee.badge_status == val).count()
            shiny_counts[desc] = shiny_sponsors.filter(Attendee.badge_status == val).count()

        return {
            'sponsor_counts': sponsor_counts,
            'shiny_counts': shiny_counts,
        }

    def attendance_graph(self, session):
        graph_data_current_year = RegistrationDataOneYear()
        graph_data_current_year.query_current_year(session)

        return {
            'current_registrations': graph_data_current_year.dump_data(),
        }

    @csv_file
    def accessibility_report(self, out, session):
        out.writerow([
            'Badge Name',
            'Badge Number',
            'Email',
            'Desired Accommodations',
            'Other Desired Accommodations'
        ])

        accessibility_request_attendees = session.query(Attendee).filter(Attendee.accessibility_requests != '').all()

        for attendee in accessibility_request_attendees:
            out.writerow([
                attendee.badge_printed_name,
                attendee.badge_num,
                attendee.email,
                ", ".join(attendee.accessibility_requests_labels),
                attendee.other_accessibility_requests
            ])

    @csv_file
    def full_dealer_report(self, out, session):
        out.writerow([
            'Business Name',
            'Dealer Name',
            'Email',
            'Tables',
            'Badges',
            'Status',
            'Amount Paid',
            'Website URL',
            'Wares',
            'Wares - Other',
            'Description',
            'Special Needs',
            'Review Notes',
            'Admin Notes',
            'Power Requested',
            'Power Request Info',
            'Location'
        ])
        dealer_groups = session.query(Group).filter(Group.tables > 0).all()
        for group in dealer_groups:
            if group.is_dealer:
                full_name = group.leader.full_name if group.leader else ''
                out.writerow([
                    group.name,
                    full_name,
                    group.leader.email if group.leader else '',
                    group.tables,
                    group.badges,
                    group.status_label,
                    group.amount_paid,
                    group.website,
                    group.categories_labels,
                    group.categories_text,
                    group.description,
                    group.special_needs,
                    group.review_notes,
                    group.admin_notes,
                    group.power,
                    group.power_usage,
                    group.location
                ])

    @csv_file
    def dealers_publication_listing(self, out, session):
        out.writerow([
            'Business Name',
            'Description',
            'URL',
            'Location'
        ])
        dealer_groups = session.query(Group).filter(Group.tables > 0).all()
        for group in dealer_groups:
            if group.is_dealer and group.status_label == 'Approved':
                out.writerow([
                    group.name,
                    group.description,
                    group.website,
                    group.location
                ])

    @csv_file
    def dealer_memberships_report(self, out, session):
        out.writerow([
            'Full Name',
            'Legal Name',
            'Business Name',
            'Group Status'
        ])
        dealers = session.query(Attendee).join(Attendee.group).filter(
                                Group.tables > 0).filter(Group.status.in_([c.UNAPPROVED, c.APPROVED, c.WAITLISTED]))
        for dealer in dealers:
            if dealer.is_dealer and dealer.first_name:
                out.writerow([
                    dealer.full_name,
                    dealer.legal_name,
                    dealer.group.name,
                    dealer.group.status_label,
                ])

    @csv_file
    def illinois_department_of_revenue_report(self, out, session):
        out.writerow([
            'Business Name',
            'Point of Contact',
            'Street Address',
            'Street Address (2)',
            'City',
            'Region',
            'Zip',
            'Country',
            'Email',
            'Phone Number',
            'Tax Number'
        ])
        dealer_groups = session.query(Group).filter(Group.tables > 0).all()
        for group in dealer_groups:
            if group.is_dealer and group.status_label == 'Approved':
                full_name = group.leader.full_name if group.leader else ''
                out.writerow([
                    group.name,
                    full_name,
                    group.address1,
                    group.address2,
                    group.city,
                    group.region,
                    group.zip_code,
                    group.country,
                    group.leader.email if group.leader else '',
                    group.leader.cellphone if group.leader else '',
                    group.tax_number
                ])

    def dealer_cost_summary(self, session, message=''):
        paid_groups = session.query(Group.power_fee, Group.name, Group.tables, Group.cost).filter(Group.amount_paid > 0)
        custom_fee_groups = paid_groups.filter(Group.auto_recalc == False)
        auto_recalc_groups = paid_groups.filter(Group.auto_recalc == True)
        table_cost_list = defaultdict(int)
        for num, desc in c.TABLE_OPTS:
            table_cost_list[desc] = auto_recalc_groups.filter(Group.tables == num).count() * c.TABLE_PRICES.get(num)

        return {
            'now': localized_now(),
            'message': message,
            'num_custom_groups': custom_fee_groups.count(),
            'num_auto_groups': auto_recalc_groups.count(),
            'table_breakdown': table_cost_list.items(),
            'table_sum': sum(table_cost_list.values()),
            'badge_sum': session.query(Attendee).join(Attendee.group).filter(Attendee.paid == c.PAID_BY_GROUP,
                                                                            Attendee.is_dealer == True,
                                                                            Group.amount_paid > 0,
                                                                            Group.auto_recalc == True).count() * c.DEALER_BADGE_PRICE,
            'custom_fee_sum': sum([group.cost for group in custom_fee_groups]),
            'power_fee_sum': sum([group.power_fee for group in auto_recalc_groups]),
        }

    @csv_file
    def dealers_application_review_report(self, out, session):
        out.writerow([
            'Business Name',
            'Dealer Name',
            'Tables',
            'Website URL',
            'Email',
            'Wares',
            'Wares - Other',
            'Description',
            'Special Needs',
            'Review Notes',
            'Admin Notes',
            'Power Requested',
            'Power Request Info'
        ])
        dealer_groups = session.query(Group).filter(Group.tables > 0).all()
        for group in dealer_groups:
            if group.is_dealer and group.status_label == 'Pending Approval':
                full_name = group.leader.full_name if group.leader else ''
                out.writerow([
                    group.name,
                    full_name,
                    group.tables,
                    group.website,
                    group.leader.email if group.leader else '',
                    group.categories_labels,
                    group.categories_text,
                    group.description,
                    group.special_needs,
                    group.review_notes,
                    group.admin_notes,
                    group.power,
                    group.power_usage
                ])

