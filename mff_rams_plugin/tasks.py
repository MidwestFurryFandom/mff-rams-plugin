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
        badge = session.attendee(badge_id)
        if badge.managers:
            pit_badge = badge.managers[0].pit_badge
            if pit_badge and not badge.managers[0].paid_minors:
                pit_badge.badge_status = c.INVALID_STATUS
                session.add(pit_badge)
            session.commit()