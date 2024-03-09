from collections import defaultdict

from uber.config import c
from uber.decorators import cost_calculation, credit_calculation
from uber.receipt_items import Group

Group.cost_changes['power'] = ('Power Level', "calc_group_price_change")
Group.cost_changes['power_fee'] = ('Custom Power Fee', "calc_group_price_change")

@cost_calculation.Group
def table_cost(group):
    table_count = int(group.tables)

    if not table_count or not group.auto_recalc:
        return
    if group.table_fee:
        return ("Custom Fee for {}".format(group.tables_repr), group.table_fee * 100)
    
    return ("{} Fee".format(group.tables_repr), c.TABLE_PRICES.get(table_count) * 100, None)

@cost_calculation.Group
def power_cost(group):
    if not group.auto_recalc:
        return None

    if group.default_power_fee:
        return ("Tier {} Power Fee".format(group.power), int(group.default_power_fee) * 100, 'power')
    elif group.power_fee:
        return ("Custom Fee for Tier {} Power".format(group.power), group.power_fee * 100, 'power_fee')
