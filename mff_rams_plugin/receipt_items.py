from collections import defaultdict

from uber.config import c
from uber.decorators import cost_calculation, credit_calculation
from uber.models import Attendee

@cost_calculation.Group
def table_cost(group):
    table_count = int(group.tables)

    if not table_count:
        return
    if group.table_fee:
        return ("Custom Fee for {}".format(group.tables_repr), group.table_fee * 100)
    
    return ("{} Fee".format(group.tables_repr), c.TABLE_PRICES.get(table_count) * 100)

@cost_calculation.Group
def power_cost(group):
    if group.auto_recalc and group.default_power_fee:
        return ("Tier {} Power Fee".format(group.power), int(group.default_power_fee) * 100)
    elif group.power_fee:
        return ("Custom Fee for Tier {} Power".format(group.power), group.power_fee * 100)