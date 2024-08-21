from collections import defaultdict
from datetime import timedelta
from pockets.autolog import log
from pathlib import Path

from uber.config import c, Config, dynamic, parse_config, request_cached_property
from uber.menu import MenuItem
from uber.utils import localized_now

config = parse_config("mff_rams_plugin", Path(__file__).parents[0])
c.include_plugin_config(config)

c.MENU.append_menu_item(
    MenuItem(name='Midwest FurFest', submenu=[
        MenuItem(name='Comped Badges', href='../mff_reports/comped_badges'),
        MenuItem(name='Daily Attendance', href='../mff_reports/attendance_graph'),
    ])
)

c.MENU['People'].append_menu_item(MenuItem(name='Promo Codes',
                                               href='../promo_codes/index'), position=3)


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
    def DEALER_POWER_OPTS(self):
        power_opts = []
        for count, desc in sorted(c.DEALER_POWERS.items()):
            if count == 0:
                power_opts.append((count, desc))
            else:
                price_info = ": ${}".format(c.POWER_PRICES[count])\
                    if c.POWER_PRICES.get(count) else ""
                power_opts.append((count, 'Tier {}{} {}'.format(count, price_info, desc)))
        return power_opts
    
    @property
    def PREREG_DEALER_POWER_OPTS(self):
        return [(-1, "Select a Power Level")] + self.DEALER_POWER_OPTS
    
    @property
    def HOTEL_LOTTERY_OPEN(self):
        return c.AFTER_HOTEL_LOTTERY_START and c.BEFORE_HOTEL_LOTTERY_DEADLINE
    
    def get_table_price(self, table_count):
        return self.TABLE_PRICES[table_count]
    
    def get_badge_count_by_type(self, badge_type):
        # Since sponsor and shiny sponsor badges are upgrades with limited availability,
        # this expands how they're counted to match how preordered merch is counted
        from uber.models import Session, Attendee
        with Session() as session:
            count = session.query(Attendee).filter_by(badge_type=badge_type).filter(
                    ~Attendee.badge_status.in_([c.INVALID_GROUP_STATUS, c.INVALID_STATUS, 
                                                c.IMPORTED_STATUS, c.REFUNDED_STATUS])).count()
        return count

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

    @request_cached_property
    @dynamic
    def SOLD_OUT_BADGE_TYPES(self):
        opts = []

        if not self.SPONSOR_BADGE_AVAILABLE:
            opts.append(self.SPONSOR_BADGE)
        if not self.SHINY_BADGE_AVAILABLE:
            opts.append(self.SHINY_BADGE)

        return opts
    
    @request_cached_property
    @dynamic
    def FORMATTED_BADGE_TYPES(self):
        badge_types = []
        if c.AT_THE_CON and self.ONE_DAYS_ENABLED:
            if self.PRESELL_ONE_DAYS and localized_now().date() >= self.EPOCH.date() or True:
                day_name = localized_now().strftime('%A')
                if day_name in ["Friday", "Saturday", "Sunday"]:
                    price = self.BADGE_PRICES['single_day'].get(day_name) or self.DEFAULT_SINGLE_DAY
                    badge = getattr(self, day_name.upper())
                    if getattr(self, day_name.upper() + '_AVAILABLE', None):
                        badge_types.append({
                            'name': day_name,
                            'desc': "Can be upgraded to an Attendee badge later.",
                            'value': badge,
                            'price': price,
                        })
            elif self.ONE_DAY_BADGE_AVAILABLE:
                badge_types.append({
                    'name': 'Single Day',
                    'desc': "Can be upgraded to an Attendee badge later.",
                    'value': c.ONE_DAY_BADGE,
                    'price': self.DEFAULT_SINGLE_DAY
                })
        badge_types.append({
            'name': 'Attendee',
            'desc': 'Allows access to the convention for its duration.',
            'value': c.ATTENDEE_BADGE,
            'price': c.get_attendee_price()
            })
        for badge_type in c.BADGE_TYPE_PRICES:
            if c.PRE_CON or badge_type not in c.SOLD_OUT_BADGE_TYPES:
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
            # We don't ACTUALLY presell one day badges, we just need them split up into days
            # Also, the event is open Thursday but we do not sell Thursday badges
            if self.PRESELL_ONE_DAYS and localized_now().date() >= self.EPOCH.date():
                day_name = localized_now().strftime('%A')
                if day_name in ["Friday", "Saturday", "Sunday"]:
                    price = self.BADGE_PRICES['single_day'].get(day_name) or self.DEFAULT_SINGLE_DAY
                    badge = getattr(self, day_name.upper())
                    if getattr(self, day_name.upper() + '_AVAILABLE', None):
                        opts.append((badge, day_name + ' Badge (${})'.format(price)))
            elif self.ONE_DAY_BADGE_AVAILABLE:
                opts.append((self.ONE_DAY_BADGE, 'Single Day Badge (${})'.format(self.ONEDAY_BADGE_PRICE)))
        return opts


# TODO: Why do we need to redefine this?
c.TERMINAL_ID_TABLE = {k.lower().replace('-', ''): v for k, v in config['secret']['terminal_ids'].items()}


c.STATIC_HASH_LIST = {
    "fullcalendar-5.3.2/examples/js/theme-chooser.js": "sha384-w5FSPeW6DBrsVHTk/juh/qrSOKuxuqkRcgf+J8hPe+2yZj87TCF1q5sp/l2zV9pm",
    "fullcalendar-5.3.2/lib/locales/pt.js": "sha384-7+VczF+AmlizfN7o1c26UG039Y1ZHMDtmUrAb7N/IVp5kxZHWrrg2oMYnL46c9v6",
    "fullcalendar-5.3.2/lib/locales/en-nz.js": "sha384-HTUIX2CyeGhd2YMNxO7b180B15DD5sdlwd+EFDtPwt5BMSi6cMGtHNjCiAknpiqG",
    "fullcalendar-5.3.2/lib/locales/vi.js": "sha384-X5RvGjBSXSqlqyEDz0i0XIAdqPIRqhc3QMzepotljxg1iUOVniKyzjkaQZL1haUg",
    "fullcalendar-5.3.2/lib/locales/lv.js": "sha384-iju09bSwoVT8solC+JthV8SRLUqhqJ3C/tI8cvudBW1NnppjJOUJ5ghig3UxA/97",
    "fullcalendar-5.3.2/lib/locales/kk.js": "sha384-8iOWoUcc+amfswFCHvip4XePng90Tvlm+ujRqeW9Q/LJAzxMenLJRJZwACe4jzx4",
    "fullcalendar-5.3.2/lib/locales/gl.js": "sha384-iMmASu0PSb8fd/xlY6KCl7e4UO6PwPBi2Z/qBqF4zSlwpUkILSAyoMd3SCUiHpIh",
    "fullcalendar-5.3.2/lib/locales/pl.js": "sha384-Kg9TEH1Eb/Vw/rAz9cR5vE8bUyGkkPs/Dr9j+Q2PZPAbqN/LdtEYXJTINcl+3xn3",
    "fullcalendar-5.3.2/lib/locales/el.js": "sha384-gD70IhWaLmS10OhQX41Tygdh3lJZpULytl4I7ZsAMHE2J1z6W24kVMBMZMyqzQYy",
    "fullcalendar-5.3.2/lib/locales/et.js": "sha384-RA4JBotaNRpx1Pc5RiipwrTGymGF/7dZNOtMJv/9bt2r0vGqeHpjtwyhtWhQG/eY",
    "fullcalendar-5.3.2/lib/locales/is.js": "sha384-pfbyvZDfkxYTkY7AFaLq/EAu1lcogLDXlnA3CHxUXuWvyczmC2DOfPnRkzuNh9g+",
    "fullcalendar-5.3.2/lib/locales/sl.js": "sha384-FntiNJzI7tVHu7z9omsz0grCsVQ07MenbqCkqMdNbga98/8AlhqC0Q58lYSRNjpF",
    "fullcalendar-5.3.2/lib/locales/nn.js": "sha384-2+xuHpH9SEbwC4Xinzs93njXkZvWKepYUW2HTL7hapFEDnhpuYK2PPDbVd9HMaCl",
    "fullcalendar-5.3.2/lib/locales/ko.js": "sha384-nJnOucnSSOgG+TFGPKApOT5aQw99obc8E27SNoQjQJxsas6m5KPntWXO2+CX/Zsk",
    "fullcalendar-5.3.2/lib/locales/ar-sa.js": "sha384-xJNyxrLsIa5eYskHxA8CobPk124Jws+V94rSg1WaZNffFGozQcxEiiuK1mjLkCeJ",
    "fullcalendar-5.3.2/lib/locales/hr.js": "sha384-cjhDMWFtTcZmuvRKSGeEEZeUEVDtRU1sAsIJvkvHN8Rl1nyLqoYyktdxhL2CNgM6",
    "fullcalendar-5.3.2/lib/locales/ms.js": "sha384-+4iARIcCsuWu03QuPewo0XFAT7D92gfVtW9J4+KqwrV+DrZPcisaoo2bEoY58yDW",
    "fullcalendar-5.3.2/lib/locales/fi.js": "sha384-AYDSmVEU0J33rXDDx+p7PPQ2X2f8BUvC0XJgf34u3DGRrCaH3ioIlDzNnB1ZOQt9",
    "fullcalendar-5.3.2/lib/locales/th.js": "sha384-SsdqZ6kwrVzVVEvztdMtoIimnwndqN06MysSkK6MCb3S+bFBKhAUel6pRZAB3OrC",
    "fullcalendar-5.3.2/lib/locales/ru.js": "sha384-bFPD82pabPDM/mVhxLQRrfR8b49pv/euPPVyuRF7wUguoyKvYhKTccJgrNNHD3SW",
    "fullcalendar-5.3.2/lib/locales/eu.js": "sha384-PfDQoQKKPhMdw606BK3l9JTgfYhg1Mg1o5+6AkwM/JdjL4jLOZhBkx8Wmzo0vmab",
    "fullcalendar-5.3.2/lib/locales/mk.js": "sha384-2j/ZDhZME9kLj92LnF7PAN+DTAHWrZMbmRgAtuLUkL70N+PnTIm1yUuy3LKHHpMB",
    "fullcalendar-5.3.2/lib/locales/sq.js": "sha384-9GdkP5dKauvmj/h3j5viWxjhwudaIX1IWo5s2T8A4MbT4/vTMcwPZhNOJ0e+gWga",
    "fullcalendar-5.3.2/lib/locales/ja.js": "sha384-1VmNsrCZhq4kdfVKJ7u+xFdGSSHoiyBxl9khTV8UTM51BCHESP5yTYjJnFE+ITeY",
    "fullcalendar-5.3.2/lib/locales/ka.js": "sha384-nQOMDr/rlMFpnTimKB212qx1WR7VHWardUUBm7yt/ExBejDI5FSA0gtpFy6tXiZF",
    "fullcalendar-5.3.2/lib/locales/he.js": "sha384-0EurjIZamxAQnLS1e0RaQfu2aK5pb9HgiprqIUcj88rzJoa8enF628VozsvhJv/V",
    "fullcalendar-5.3.2/lib/locales/ug.js": "sha384-Qfo54sJnE4Rhbrg2V1ijlEExFPU7S1lzvfctKGvSxhkVuyR7l/pLMcc6K+S5sY7e",
    "fullcalendar-5.3.2/lib/locales/bg.js": "sha384-IecRJ/t3T0dQ0r3UkIwd45CY6swwIKs3TEnCGxsiRjaKQrukToiuRO6onDNEI2wo",
    "fullcalendar-5.3.2/lib/locales/sr-cyrl.js": "sha384-Zv87B6JmKiUcyIy8cjJCGMvhhHFOPqWW0FVSZQlY4BJG2t9LGt6CV3ki6ZCoDBLh",
    "fullcalendar-5.3.2/lib/locales/uz.js": "sha384-ZZMtXQEWLUUihHgMfdWcii9rxZKEirNGJ1Y8RgZ6qc47wkqLZk+Of9uzOB/MFhB7",
    "fullcalendar-5.3.2/lib/locales/ar-tn.js": "sha384-xPmIvV1ZyO+zfAfceT+KLN+7vgJnqRGPy/1SGblrUTe0Iw4YKtCGVNgHKrNi1zyx",
    "fullcalendar-5.3.2/lib/locales/ne.js": "sha384-3gf9ERCVzW3PCI5e7Pwj6nus96WqUfMRdciqPwlr1meS08KsYqoz7tygct2OvF4/",
    "fullcalendar-5.3.2/lib/locales/af.js": "sha384-9wzGIZrzGo8kaxDGzxeMDQt3xtuAmB7ckm+TBoXRcj3U9MOW9yC0ElJuvALPOGmt",
    "fullcalendar-5.3.2/lib/locales/fr-ch.js": "sha384-zqUJFwJoeIedgzYabUVKBy0Hpd0IIrwqb+SYP6yiJ18nw1B4GGRMfPvhthousGS2",
    "fullcalendar-5.3.2/lib/locales/es-us.js": "sha384-V+ogbbHm4Ffd3/0UzN3wN3q9q8obN/2mP+y8ecAZyHNhzRYry9mllhq8heI+2M1Z",
    "fullcalendar-5.3.2/lib/locales/id.js": "sha384-01OviFaC8ze3LX8KNHx2ID7+5aWI8TNMRNvt5CyTzOpQnwxu2QZdmboMmNfnO9+1",
    "fullcalendar-5.3.2/lib/locales/az.js": "sha384-x8TvxE9s1zmu5P4M7rV/TQp1RN/sXXpIxScsiRjGQJkcVclNx0Qg+osisB3mrqUV",
    "fullcalendar-5.3.2/lib/locales/en-au.js": "sha384-PY6q11/FesrOvlfIyvxtvFFdFhBwZndSSM+LQrgrSc1Jo0mJ0bkCVnkpf0Q2J9VR",
    "fullcalendar-5.3.2/lib/locales/lb.js": "sha384-qznVwajnnlQHfgnD0B0qxrBR/wAb6k9bdvivdmjPQdVYODewZFomiqCkvdnY8BPY",
    "fullcalendar-5.3.2/lib/locales/ca.js": "sha384-/MJYRBixvN80rXbO66YJdiJ33fC/YslFTaivPm4JfxKpVr6K2Pd9WJ/ebvHnjPGa",
    "fullcalendar-5.3.2/lib/locales/nb.js": "sha384-UGRr28w3ge2YbGrw3t+vHTPtr7h7JXQWntJQFtliqEo6bN20o9iu/6Tu6KbQ1hN3",
    "fullcalendar-5.3.2/lib/locales/ar-kw.js": "sha384-Iz8qJTEGd+qzUoyR3+5FoWGxB8cw0j2xoCiV3OjmpA7UYSUB0zY8vTJe4cJYzhXq",
    "fullcalendar-5.3.2/lib/locales/zh-cn.js": "sha384-s+iDTEMYl65COf7tEw4WMDNIQIfY1SsoijZceecS3eA8tezjU07628aMbg93LCLZ",
    "fullcalendar-5.3.2/lib/locales/zh-tw.js": "sha384-KV4+TVy21Q+DR7u5bzndvijyZzjjSuOffPg1ApZOyGixfXQG/Nk4oTHatrodi8Nz",
    "fullcalendar-5.3.2/lib/locales/pt-br.js": "sha384-w1mxe4/ZTcTHJRajJa1p3SDg+sg4Eqjk5qajZhrQgAlBTrdTgQSJAmjX7RTj6zcm",
    "fullcalendar-5.3.2/lib/locales/da.js": "sha384-OMEYfZdB3A8ceGTupabOuC8at49j0sI4/kXIIWZE6LFico6B3YLeshYFakaY6BCQ",
    "fullcalendar-5.3.2/lib/locales/fa.js": "sha384-v0FLfNTKd2lKKo7eQE+Ztr8PkQVx/oGCiXujFYT2HRzRSow7OYfzs41yLUFsTMUD",
    "fullcalendar-5.3.2/lib/locales/de.js": "sha384-+Q96nUj+LbqpwHJd1xCLTedEmfguWFI3IPh3hqB9KMj7BfvkFCbG6VVvEjNxhl5R",
    "fullcalendar-5.3.2/lib/locales/bs.js": "sha384-7pdZJS5CXPAEUdKr8KUKrixZZsSNt0uDYq1LAKQU/k/mh9Vn5qKMog/IV+p9y2Ad",
    "fullcalendar-5.3.2/lib/locales/sv.js": "sha384-DUHimB9L77Px3Csm74b5C70fAVVRPju8JFMJ4MOVsemFdiouZUxseMhL+G/XQnVN",
    "fullcalendar-5.3.2/lib/locales/hi.js": "sha384-lAIZoRFNDdtHIfiF4z16U6lqWWf0RpfrQ70P/jJPxmaiI/cRFIp3snk7Xu71sT2E",
    "fullcalendar-5.3.2/lib/locales/uk.js": "sha384-hoO1pqNaCIEmrV7FJ3tibLlFoK6Iiaw7M2jz8kjZi3ICfcrO1t3BsYOryl74AsZb",
    "fullcalendar-5.3.2/lib/locales/ar-dz.js": "sha384-qbhODfgsENhspZrNxW/mDlNAVDGjjXth0pRUp3PAP5xgDHpV1HxE6odQ+3ro03yO",
    "fullcalendar-5.3.2/lib/locales/cs.js": "sha384-hHChitqsvN7M2NhGeadV9oadJqyqborxJ7ltweHzVB8F1km/Yqu0KVFEVyJrNl8r",
    "fullcalendar-5.3.2/lib/locales/fr.js": "sha384-AjEDGfRVprrADLUaRt2vlC7bBEpdWzNMn0ck74O2y5PYkCkRE8wZIsnsD64COB4I",
    "fullcalendar-5.3.2/lib/locales/nl.js": "sha384-3RB5dAjouWRQgo6OYsiuFTj9WQKTY0bD5nUC6K4jjxFfznXOv3hYBBto/8rGaLI1",
    "fullcalendar-5.3.2/lib/locales/fr-ca.js": "sha384-CQ0drL68Af6DSCebjVrCjtRFo0j2WCcsHNExmr0jSiEfmADFZFUJQvf6FyOPhoNn",
    "fullcalendar-5.3.2/lib/locales/en-gb.js": "sha384-zOH5OU5j5qdrK7BBEO6Uviyo8VFQw+tTUT4ypUVbMooHGHfQub2uEKDNtq3RehmP",
    "fullcalendar-5.3.2/lib/locales/sr.js": "sha384-RmvYetAPsfgBeY4lJ227tGba/9lVYlUSvcmidfIB8loBng6oo1I1i5oJc3q52x5e",
    "fullcalendar-5.3.2/lib/locales/hu.js": "sha384-zgG99q7Fxj4AYtks0djVgFDlyQE47/FAo4cj2OdhPd8iGSAscXvNeciNixfWeq+6",
    "fullcalendar-5.3.2/lib/locales/lt.js": "sha384-T5qQ0Q2+dFyZOW3YnfZB5a9am/GkeHWnWg1z8e7xmenRhpnKFI894PwoPPRoEyFe",
    "fullcalendar-5.3.2/lib/locales/ar-ma.js": "sha384-lXnukFWsOLgmGV8yejV+7CFmUpPT/HPxBIUQL1DsCxTDHBiRf2EJOQNNr5nqO5SV",
    "fullcalendar-5.3.2/lib/locales/ar.js": "sha384-SbC961TeIVTxkPSB3tyTYnKihwTVEQ4M3JIvhnGWkslTzJo/uWdW9AEWKdcY4DMO",
    "fullcalendar-5.3.2/lib/locales/ar-ly.js": "sha384-BB1QbnwPuB3x9qlkxtG+GmvMO+gj8jUNSmuLmUKG890DTChvZ4d1c1pvUdwueo8Y",
    "fullcalendar-5.3.2/lib/locales/sk.js": "sha384-I3VtUMf/fRWRMzQS2FEFKpBIT7qZMwtPtmZFueUUo6+iA5Du1v33wsYWeHRRQ2rs",
    "fullcalendar-5.3.2/lib/locales/it.js": "sha384-ClUyQ9VPaCcq8zHT2RcUagiWItJI3j8cNxhSubxujEKTRELhLkUIqiSZKEU0Q/Vi",
    "fullcalendar-5.3.2/lib/locales/es.js": "sha384-Rcd5NBSXUeRUueO2LTjdxpJeiDXFrnyDVCkAQciJ0mh8xuYwbooV9bKh83LSTxqR",
    "fullcalendar-5.3.2/lib/locales/ro.js": "sha384-4or5XbAz2xsge2/HwpjEh1yV7sOutrNNd/HwqzypS4MqNxlDUvSOnjWX6bWaaREO",
    "fullcalendar-5.3.2/lib/locales/tr.js": "sha384-AnV7+M1w7ClRdSiDtKQ1Oly45lQRPBcPgHRPziNKFLtfA8AZkErLo7RE/yWQ1Sbl",
    "fullcalendar-5.3.2/lib/main.min.css": "sha384-yjrybFBlOUqJTxkBPExX0Yr2cKvvIoK8keRp9dI8LWMCXwNcaYBBrkCXLGrP6Xld",
    "fullcalendar-5.3.2/lib/main.min.js": "sha384-23Pl3/wHt59Pxhxs0ZkVndXJcnlxXNO41+BmixrAYZjAFAzwtVZQnd3I9BxMG1MS",
    "fullcalendar-5.3.2/lib/main.css": "sha384-Isk/ThH3QeGwUVpHLenmeelOf7bsvapM7vra13kJwjXDQXO42BCT1Yhx/4faCWPm",
    "fullcalendar-5.3.2/lib/main.js": "sha384-1Gk3PslZaZU8EEzESD+jT7CZwmyxB+jDFrxpCWoNURUWe5QVWHF5FH33osXwJP42",
    "fullcalendar-5.3.2/lib/locales-all.min.js": "sha384-9DSjmB5snkwTpF4UkLpUAUXKCCcL3Kq4Q6qunUiHFlwynxem0fBKSB/Pdz+4dDL3",
    "fullcalendar-5.3.2/lib/locales-all.js": "sha384-x4145WV6VZ8HGF2fYYuIUBHxjQyYrj63XpMs5F9Wabt3p8qsSpFb7jZARJtdQTnh",
    "js/common-static.js": "sha384-75eWtizzova4ZxRETusdqkk05zrFfYzYWCmoUYlawGuwv8msiP+MxMKjO5kziAuK",
    "js/moment.js": "sha384-7e6uR49PcQsrLgfr25C6sHp5owxwt+kkiaby+/PMbG4xw0FKp1d49+WllI8AicB/",
    "js/warn-before-logout-dealer.js": "sha384-OXrEL7xAoSb+ANl19Ersw+KAlXTYfY0RsPnCNnSV0728UrqNtP0qmydzITZC6czF",
    "js/warn-before-logout.js": "sha384-5PRxRUAXPZOR80tka4DE5DZp9V3v/+lpP1TuesQwDA8bvZQ6J5xBL30OPZGFgFYu",
    "js/window-hash-tabload.js": "sha384-b2qQksK/cBW+BSR9DLuIiJ44BZjsOjbp121J7Djx9sqfZdXnwNFYI/XfKdaP7kFX",
    "js/bootstrap.min.js": "sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa",
    "js/resend-email-form.js": "sha384-0DrGI9T89PbsaRQAON4vAlUFPqv5BQbEl64Vct3NMfMz6b7JDBg2gerZLrCumIkw",
    "js/jquery-3.1.1.min.js": "sha384-3ceskX3iaEnIogmQchP8opvBy3Mi7Ce34nWjpBIwVTHfGYWQS9jwHDVRnpKKHJg7",
    "js/badge_num_barcode.js": "sha384-/SnNKSIYNqoKfPQPzjlVzOGhKprpwnfULI10YIO53t3TL2ESShXD8zqgos8XsCkz",
    "js/servertimecheck.js": "sha384-Y5HavH5aTQVEYJlpWLWAwJ+k2ojugn6r533PoMGcznySyW9Uzq5PAZxyjsAKrqrT",
    "js/load-attendee-modal.js": "sha384-8lGUJFplMQ3ervQ4EZBhl6Zxf+PGlCCwQFXj3mqcysEEFzgvVdTNiTza+/KgKOFh",
    "js/check-duplicate-email.js": "sha384-/APjfl/cVRBfLU8+wA5ZSegLaUtMkZcNur2c+SBowl4buJZp6hv3ngGt6iT9Vqna",
    "styles/bootstrap.min.css": "sha384-kBDxMwTPdHoj6gazpsPy4h8BnD8sU4Jeo7NbWJ0H03VMluDI3/F9mwnXMZUUkhwB",
    "styles/styles.css": "sha384-q761r8ICTniYVjj/GZ0VyIVOT9yCO43MR5cspXcTGJpNLtd95PWkHxdoTlF4Lc7b",
    "styles/login.css": "sha384-tKT6+xUzjqdQAhN/87ZGyqhXpazxNuXTF24z2CxXdCPs7XJDCUgj5WIynPxWGOsf",
    "theme/prereg.css": "sha384-D+G/Wl80zewz1Mx9jsjqQB5sJO9TjJXC/yWfMQSSfYOB9RAGbW2WPWLcH32G7jnY",
    "theme/prereg_extra.css": "sha384-1Y2O5xB/ObfxLxE/FH0iH6/XdsbKdTIHvDGSDP7coXZEH+RhmaDXBPCAYva0yube",
    "deps/selectToAutocomplete/jquery-1.11.1.min.js": "sha384-UM1JrZIpBwVf5jj9dTKVvGiiZPZTLVoq4sfdvIe9SBumsvCuv6AHDNtEiIb5h1kU",
    "deps/selectToAutocomplete/jquery-ui.min.js": "sha384-TkwOpfRia7iUdElqSOlUgVT6+cZb8lR/wsXT91RPkrUYQAoCyG3SlfVX8c0Ey5IR",
    "deps/selectToAutocomplete/jquery.select-to-autocomplete.js": "sha384-qUnRY5v9UDiLpcdltjLZlygKiMN2Atj4Ayqp+/YJKRIs/GW1mdEvDuFLohZ9VtIe",
    "deps/selectToAutocomplete/jquery-ui.css": "sha384-+AtlTJbWDkXeuZPY5QE2fE/Y9ASHvGiOEOalfkgCup137/ePKyE7d410ZTPdj6j0",
    "deps/combined.css": "sha384-hWvvvtNskIFIkMQ2Awjfavyf3q5hJuBfm6nvSeNIogGxD1xfKAW71EkcgOMFgeB5",
    "deps/jquery-datetextentry/jquery.datetextentry.js": "sha384-YYLzV0F3OjgMqSlWJnPpkiryR11dMO8nXkBpgeLy5S3qu22uZz3dukciNcBR9Zfc",
    "deps/jquery-datetextentry/jquery.datetextentry.css": "sha384-aAjyN5r8ognDOt6BGc35M+KRFLevxfl+QXzMSltKZT+L/6S5UWuymBgsm/c11+nF",
    "deps/bootstrap5/bootstrap.min.css": "sha384-xJIFK/p04lbzZl/Ns+M1F5x8wOyjx3FZEbz1HRS5JsBb0vKd+A91Cu42gthIW62W",
    "deps/bootstrap5/bootbox.all.min.js": "sha384-Iuvblri4OHq06GlDWnUaUNcMgpaj3AiGTiPSVw7PXtEDPu4lj52RmmmEZsW5jL74",
    "deps/bootstrap5/bootstrap.bundle.min.js": "sha384-MrcW6ZMFYlzcLA8Nl+NtUVF0sA7MsXsP1UyJoMp4YLEuNSfAP+JcXn/tWtIaxVXM",
    "deps/bootstrap5/font-awesome.min.css": "sha384-CuwP2ckM9Wo6xqj5tG9ZruVMIloIkLp2rqByE1eAQT0dhFF1hYmCB6zTC2SH2nUo",
    "deps/bootstrap5/datatables.min.js": "sha384-QnRWMr7ovUzHcmPtJ5Q8qta414c7t0+KUSwXKZgF9Y1E3AomxiPtUkeqQDmee6A9",
    "deps/bootstrap5/datatables.min.css": "sha384-XAiOl202UZGdRoWVCZE6iPUqhR2sU8WZ+hC0c6gMyhqWpvM9CqBzxSlDkXN1+VbX",
    "deps/combined.min.css": "sha384-sLLIZQ8+GwwvnQlFirTtCQxy4A40yZ4YL5P5vpD9rYifX0igQ27Sg+juffvAGUvo",
    "deps/bootstrap3/bootstrap.min.css": "sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u",
    "deps/bootstrap3/bootbox.min.js": "sha384-Nk2l95f1t/58dCc4FTWQZoXfrOoI2DkcpUvgbLk26lL64Yx3DeBbeftGruSisV3a",
    "deps/bootstrap3/bootstrap.min.js": "sha384-ps2NNIYlSNpyZnGQAdEdsbpck7e3ivHY61DS3FhrUD2g8l1i3btgkq+Xojxa3Lot",
    "deps/bootstrap3/datatables.min.js": "sha384-MJvRkOGDXCHH7fdjYo3xFwID7sxICUuzZl9Qr/0rbkjPoSHLu+w9ODkS5fEKdSa5",
    "deps/bootstrap3/datatables.min.css": "sha384-AHUBvcqlVuPyeleZjiyek0d6LMAPwUQxBwcGYWOpKKnuHTAIZtaLgjWJJYUPKKsK",
    "deps/combined.min.js": "sha384-g8DX9ebL711cLAvlwyzbEqN31JlfSyePz+EoK99grnd3esSvWyYLKFi7IfGzVLzD",
    "deps/combined.js": "sha384-j/Z+FqSFIjn++C4ZBAEtlj/VlHybr3s9Ugu9q6Rdp0lcDCXZX1LiRkzWq/roAv4A",
    "angular-apps/tabletop_checkins/app.js": "sha384-hn9bbYGxzV84qJO0Y8pthnINI8UBIT4TWDdbx5dKFzrt1j01ipEs4G5s6RwxLDR4",
    "angular-apps/hotel/app.js": "sha384-OZAdmjED8idYTeDsN/GWV7FBWoL3iRJlPh6VSM4SWaJRld+/ODVA8Fin4aqET5Kn",
    "angular-apps/signups/app.js": "sha384-tAEyLxmaqfMg1DrR5xWsYNO0D5W+6jpojuUv1KJtMB+rUicm9TwxTls0wJiMxPno",
    "analytics/attendance.js": "sha384-VXpGRnhdaUEGkJKesCuAvmXl+7/JPQAADRFqs+Tw2D6I7zOe7mwaI8ZqNDMIJQvj",
    "analytics/lib/Chart.js": "sha384-pidppTahIu5lS8lAbKN/4L/P18UVTylkfQyGlVHDm1RbYV9R9SMSCZzlomNXLV1I",
    "analytics/analytics.css": "sha384-dkX0vm6BS1m/WlIYlYo343t7pIPnAwgTdyGJDrZpLiXkG5/7uy7XuMbu93ZqnjW6",
}