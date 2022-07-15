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

def set_credentials():
    import boto3
    import base64
    import json
    from botocore.exceptions import ClientError

    region_name = c.AWS_REGION

    # Create a Secrets Manager client
    aws_session = boto3.session.Session(
        aws_access_key_id=c.AWS_ACCESS_KEY,
        aws_secret_access_key=c.AWS_SECRET_KEY
    )

    client = aws_session.client(
        service_name=c.AWS_SECRET_SERVICE_NAME,
        region_name=region_name
    )

    def get_secret(client, secret_name):
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'DecryptionFailureException':
                # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
                log.error("Retrieving secret error: Wrong KMS key ({}).".format(str(e)))
                return
            elif e.response['Error']['Code'] == 'InternalServiceErrorException':
                # An error occurred on the server side.
                log.error("Retrieving secret error: Server error ({}).".format(str(e)))
                return
            elif e.response['Error']['Code'] == 'InvalidParameterException':
                # You provided an invalid value for a parameter.
                log.error("Retrieving secret error: Invalid parameter ({}).".format(str(e)))
                return
            elif e.response['Error']['Code'] == 'InvalidRequestException':
                # You provided a parameter value that is not valid for the current state of the resource.
                log.error("Retrieving secret error: Invalid parameter ({}).".format(str(e)))
                return
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                # We can't find the resource that you asked for.
                log.error("Retrieving secret error: Resource not found ({}).".format(str(e)))
                return
        
        # Decrypts secret using the associated KMS key.
        if 'SecretString' in get_secret_value_response:
            secret = json.loads(get_secret_value_response['SecretString'])
        else:
            return

        return secret

    signnow_secret = get_secret(client, c.AWS_SIGNNOW_SECRET_NAME)
    if signnow_secret:
        c.SIGNNOW_USERNAME = signnow_secret.get('username', '') or c.SIGNNOW_USERNAME
        c.SIGNNOW_PASSWORD = signnow_secret.get('password', '') or c.SIGNNOW_PASSWORD
        c.SIGNNOW_CLIENT_ID = signnow_secret.get('client_id', '') or c.SIGNNOW_CLIENT_ID
        c.SIGNNOW_CLIENT_SECRET = signnow_secret.get('client_secret', '') or c.SIGNNOW_CLIENT_SECRET
    else:
        log.error("Error getting SignNow secret: {}".format(signnow_secret))
	
    auth0_secret = get_secret(client, c.AWS_AUTH0_SECRET_NAME)
    if auth0_secret:
	c.AUTH_DOMAIN = auth0_secret('AUTH0_DOMAIN', '') or c.AUTH_DOMAIN
	c.AUTH_CLIENT_ID = auth0_secret('CLIENT_ID', '') or c.AUTH_CLIENT_ID
	c.AUTH_CLIENT_SECRET = auth0_secret('CLIENT_SECRET', '') or c.AUTH_CLIENT_SECRET
    else:
	log.error("Error getting Auth0 secret: {}".format(signnow_secret))

set_credentials()

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
        power_opts = []
        for count, desc in sorted(c.DEALER_POWERS.items()):
            price_info = ": ${}".format(c.POWER_PRICES[count])\
                if c.POWER_PRICES.get(count) else ""
            power_opts.append((count, 'Tier {}{} {}'.format(count, price_info, desc)))
        return power_opts

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
		
set_credentials()
