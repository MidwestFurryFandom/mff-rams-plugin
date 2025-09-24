from collections import defaultdict
from datetime import datetime, timedelta
from pockets import groupify

import stripe
import time
import pytz
from celery.schedules import crontab
from pockets.autolog import log
from sqlalchemy import not_, or_, insert
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from uber.config import c
from uber.custom_tags import readable_join
from uber.decorators import render
from uber.models import (ApiJob, Attendee, AttendeeAccount, BadgeInfo, BadgePickupGroup, Email, Group, ModelReceipt,
                         ReceiptInfo, ReceiptItem, ReceiptTransaction, Session, TerminalSettlement)
from uber.tasks.email import send_email
from uber.tasks import celery
from uber.utils import localized_now, TaskUtils
from uber.payments import ReceiptManager, TransactionRequest


@celery.task
def check_pit_badge(badge_id):
    with Session() as session:
        try:
            badge = session.attendee(badge_id)
        except NoResultFound:
            return

        if badge.managers:
            account = badge.managers[0]
            pit_badge = account.pit_badge
            pending_minors = [a for a in account.attendees if a.badge_status == c.PENDING_STATUS and 
                              a.birthdate and a.age_now_or_at_con < 18]
            if pit_badge and not account.paid_minors and not pending_minors:
                pit_badge.badge_status = c.INVALID_STATUS
            session.add(pit_badge)
            session.commit()