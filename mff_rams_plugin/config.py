from sideboard.lib import parse_config, request_cached_property
from collections import defaultdict
from datetime import timedelta
from pockets.autolog import log

from uber.config import c, Config, dynamic
from uber.menu import MenuItem
from uber.utils import localized_now

config = parse_config(__file__)
c.include_plugin_config(config)

c.MENU.append_menu_item(
    MenuItem(name='Midwest FurFest', submenu=[
        MenuItem(name='Comped Badges', href='../mff_reports/comped_badges'),
        MenuItem(name='Daily Attendance', href='../mff_reports/attendance_graph'),
    ])
)


@Config.mixin
class ExtraConfig:
    @property
    def TABLE_OPTS(self):
        return [(1, 'Single Table'),
                (2, 'Double Table'),
                (3, 'Triple Table'),
                (4, 'Quad Table'),
                (5, '10x10 Booth'),
                (6, '15x15 Suite')]

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
    def PREREG_DEALER_POWER_OPTS(self):
        power_opts = []
        for count, desc in sorted(c.DEALER_POWERS.items()):
            price_info = ": ${}".format(c.POWER_PRICES[count])\
                if c.POWER_PRICES.get(count) else ""
            power_opts.append((count, 'Tier {}{} {}'.format(count, price_info, desc)))
        return power_opts

    @request_cached_property
    @dynamic
    def SPONSOR_BADGE_COUNT(self):
        return self.get_badge_count_by_type(c.SPONSOR_BADGE)

    @request_cached_property
    @dynamic
    def SHINY_BADGE_COUNT(self):
        return self.get_badge_count_by_type(c.SHINY_BADGE)

    @property
    def PREREG_BADGE_TYPES(self):
        types = [self.ATTENDEE_BADGE, self.PSEUDO_DEALER_BADGE]
        for reg_open, badge_type in [(self.BEFORE_GROUP_PREREG_TAKEDOWN, self.PSEUDO_GROUP_BADGE)]:
            if reg_open:
                types.append(badge_type)
        for badge_type in self.BADGE_TYPE_PRICES:
            if badge_type not in types:
                types.append(badge_type)
        return types

    @property
    def FORMATTED_BADGE_TYPES(self):
        badge_types = [{
            'name': 'Attendee',
            'desc': 'Allows access to the convention for its duration.',
            'value': c.ATTENDEE_BADGE
            }]
        for badge_type in c.BADGE_TYPE_PRICES:
            badge_types.append({
                'name': c.BADGES[badge_type],
                'desc': 'Donate extra to get an upgraded badge with perks.',
                'value': badge_type,
                'price': c.BADGE_TYPE_PRICES[badge_type]
            })
        return badge_types

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
                    if day_name in ["Friday", "Saturday", "Sunday"]:
                        price = self.BADGE_PRICES['single_day'].get(day_name) or self.DEFAULT_SINGLE_DAY
                        badge = getattr(self, day_name.upper())
                        if getattr(self, day_name.upper() + '_AVAILABLE', None):
                            opts.append((badge, day_name + ' Badge (${})'.format(price)))
                    day += timedelta(days=1)
            elif self.ONE_DAY_BADGE_AVAILABLE:
                opts.append((self.ONE_DAY_BADGE, 'Single Day Badge (${})'.format(self.ONEDAY_BADGE_PRICE)))
        return opts
