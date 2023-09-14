import base64
import uuid
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from pockets.autolog import log
from sqlalchemy import func
from sqlalchemy.sql.expression import literal

from uber.config import c
from uber.decorators import all_renderable, ajax, csv_file, requires_account, render
from uber.errors import HTTPRedirect
from uber.models import Attendee, Group
from uber.tasks.email import send_email
from uber.utils import localized_now

def _prepare_hotel_lottery_headers(attendee_id, attendee_email, token_type="X-SITE"):
    expiration_length = timedelta(minutes=30) if token_type == "MAGIC_LINK" else timedelta(seconds=30)
    return {
        'KEY': c.HOTEL_LOTTERY_KEY,
        'REG_ID': attendee_id,
        'EMAIL': base64.b64encode(attendee_email.encode()),
        'TOKEN': str(uuid.uuid4()),
        'TOKEN_TYPE': token_type,
        'TIMESTAMP': str(int(datetime.now().timestamp())),
        'EXPIRE': str(int((datetime.now() + expiration_length).timestamp()))
    }

@all_renderable(public=True)
class Root:
    def index(self, session):
        pass

    @ajax
    @requires_account(Attendee)
    def check_duplicate_emails(self, session, id, **params):
        attendee = session.attendee(id)
        attendee_count = session.query(Attendee).filter(Attendee.hotel_lottery_eligible == True
                                                        ).filter(Attendee.normalized_email == attendee.normalized_email).count()
        return {'count': max(0, attendee_count - 1)}

    @requires_account(Attendee)
    def enter(self, session, id, room_owner=''):
        attendee = session.attendee(id)
        request_headers = _prepare_hotel_lottery_headers(attendee.id, attendee.email)
        response = requests.post(c.HOTEL_LOTTERY_API_URL, headers=request_headers, timeout=10)
        if response.json().get('success', False) == True:
            raise HTTPRedirect("{}?r={}&t={}{}".format(c.HOTEL_LOTTERY_FORM_LINK,
                                                       request_headers['REG_ID'],
                                                       request_headers['TOKEN'],
                                                       ('&p=' + room_owner) if room_owner else ''))
        else:
            log.error(f"We tried to register a token for the room lottery, but got an error: \
                      {response.json().get('message', response.text)}")

    @requires_account(Attendee)
    def send_link(self, session, id):
        attendee = session.attendee(id)
        request_headers = _prepare_hotel_lottery_headers(attendee.id, attendee.email, token_type="MAGIC_LINK")
        response = requests.post(c.HOTEL_LOTTERY_API_URL, headers=request_headers, timeout=10)
        if response.json().get('success', False) == True:
            lottery_link = "{}?r={}&t={}".format(c.HOTEL_LOTTERY_FORM_LINK,
                                                       request_headers['REG_ID'],
                                                       request_headers['TOKEN'])
            send_email.delay(
                    c.HOTELS_EMAIL,
                    attendee.email,
                    f'Entry link for the {c.EVENT_NAME_AND_YEAR} hotel lottery',
                    render('emails/hotel_lottery/magic_link.html', {'attendee': attendee, 'magic_link': lottery_link}, encoding=None),
                    'html',
                    model=attendee.to_dict('id'))
            raise HTTPRedirect("../preregistration/homepage?message=", f"Email sent! Please ask {attendee.full_name} to check their email.")
        else:
            log.error(f"We tried to register a token for sending a link to the room lottery, but got an error: \
                      {response.json().get('message', response.text)}")