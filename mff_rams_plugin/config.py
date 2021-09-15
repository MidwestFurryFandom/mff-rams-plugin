from sideboard.lib import parse_config, request_cached_property
from collections import defaultdict
from datetime import timedelta

from uber.config import c, Config, dynamic
from uber.menu import MenuItem
from uber.utils import localized_now

config = parse_config(__file__)
c.include_plugin_config(config)

c.MENU.append_menu_item(
    MenuItem(name='Midwest FurFest', submenu=[
        MenuItem(name='Comped Badges', href='../mff_reports/comped_badges'),
        MenuItem(name='Daily Attendance', href='../mff_reports/attendance_graph'),
        MenuItem(name='Print Adult Badges (Single Queue)',
                 href='../badge_printing/print_next_badge'),
        MenuItem(name='Print Adult Badges (1 of 2)',
                 href='../badge_printing/print_next_badge?printerNumber=1&numberOfPrinters=2'),
        MenuItem(name='Print Adult Badges (2 of 2)',
                 href='../badge_printing/print_next_badge?printerNumber=2&numberOfPrinters=2'),
        MenuItem(name='Print Adult Badges (1 of 3)',
                 href='../badge_printing/print_next_badge?printerNumber=1&numberOfPrinters=3'),
        MenuItem(name='Print Adult Badges (2 of 3)',
                 href='../badge_printing/print_next_badge?printerNumber=2&numberOfPrinters=3'),
        MenuItem(name='Print Adult Badges (3 of 3)',
                 href='../badge_printing/print_next_badge?printerNumber=3&numberOfPrinters=3'),
        MenuItem(name='Print Adult Badges (1 of 4)',
                 href='../badge_printing/print_next_badge?printerNumber=1&numberOfPrinters=4'),
        MenuItem(name='Print Adult Badges (2 of 4)',
                 href='../badge_printing/print_next_badge?printerNumber=2&numberOfPrinters=4'),
        MenuItem(name='Print Adult Badges (3 of 4)',
                 href='../badge_printing/print_next_badge?printerNumber=3&numberOfPrinters=4'),
		MenuItem(name='Print Adult Badges (4 of 4)',
                 href='../badge_printing/print_next_badge?printerNumber=4&numberOfPrinters=4'),
		MenuItem(name='Print Minor Badges',
                 href='../badge_printing/print_next_badge?minor=True'),
    ])
)


@Config.mixin
class ExtraConfig:
    @property
    def DEALER_BADGE_PRICE(self):
        return self.get_attendee_price()

    @property
    def TABLE_OPTS(self):
        return [(1, 'Single Table'),
                (2, 'Double Table'),
                (3, 'Triple Table'),
                (4, 'Quad Table'),
                (5, '10x10 Booth'),
                (6, '12x12 Suite')]

    @property
    def ADMIN_TABLE_OPTS(self):
        return [(0, 'No Table')] + c.TABLE_OPTS

    @property
    def PREREG_TABLE_OPTS(self):
        return [(count, '{}: ${}'.format(desc, c.TABLE_PRICES[count]))
              for count, desc in c.TABLE_OPTS]

    @property
    def POWER_PRICES(self):
        return defaultdict(
            lambda: config['power_prices'],
            {int(k): v for k, v in config['power_prices'].items()})

    @property
    def DEALER_POWER_OPTS(self):
        return [(0, 'No power'), (1, 'Default power')]

    @request_cached_property
    @dynamic
    def AT_THE_DOOR_BADGE_OPTS(self):
        """
        This provides the dropdown on the /registration/register page with its
        list of badges available at-door.  It includes a "Full Weekend Badge"
        if attendee badges are available.  If one-days are enabled, it includes
        either a generic "Single Day Badge" or a list of specific day badges,
        based on the c.PRESELL_ONE_DAYS setting.
        """
        opts = []
        if self.ATTENDEE_BADGE_AVAILABLE:
            opts.append((self.ATTENDEE_BADGE, 'Full Weekend Badge (${})'.format(self.BADGE_PRICE)))
        if self.SHINY_BADGE_AVAILABLE and c.SHINY_BADGE not in opts:
            opts.append(
                (c.SHINY_BADGE, '{} (${})'.format(self.BADGES[c.SHINY_BADGE], self.BADGE_TYPE_PRICES[c.SHINY_BADGE])))
        if self.SPONSOR_BADGE_AVAILABLE and c.SPONSOR_BADGE not in opts:
            opts.append((c.SPONSOR_BADGE,
                         '{} (${})'.format(self.BADGES[c.SPONSOR_BADGE], self.BADGE_TYPE_PRICES[c.SPONSOR_BADGE])))
        if self.ONE_DAYS_ENABLED:
            if self.PRESELL_ONE_DAYS:
                day = max(localized_now(), self.EPOCH)
                while day.date() <= self.ESCHATON.date():
                    day_name = day.strftime('%A')
                    price = self.BADGE_PRICES['single_day'].get(day_name) or self.DEFAULT_SINGLE_DAY
                    badge = getattr(self, day_name.upper())
                    if getattr(self, day_name.upper() + '_AVAILABLE', None):
                        opts.append((badge, day_name + ' Badge (${})'.format(price)))
                    day += timedelta(days=1)
            elif self.ONE_DAY_BADGE_AVAILABLE:
                opts.append((self.ONE_DAY_BADGE, 'Single Day Badge (${})'.format(self.ONEDAY_BADGE_PRICE)))
        return opts
		
