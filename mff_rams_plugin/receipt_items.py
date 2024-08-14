from pockets.autolog import log

from uber.config import c
from uber.decorators import receipt_calculation
from uber.models import Group


@receipt_calculation.Group
def table_cost(group, new_group=None):
    if not group.auto_recalc or new_group and not new_group.auto_recalc:
        return
    
    if not new_group:
        table_count = int(group.tables)
        if table_count:
            return (group.tables_repr, c.get_table_price(table_count) * 100, 'tables')
        return
    
    old_tables = int(group.tables)
    new_tables = int(new_group.tables)

    log.error(new_tables)

    if old_tables == new_tables:
        return
    
    if new_tables > old_tables:
        label = "Upgrade"
    else:
        label = "Downgrade"
    
    diff = (c.get_table_price(new_tables) - c.get_table_price(old_tables)) * 100
    
    return (f"{label} Table to {new_group.tables_repr}", diff, 'tables')


@receipt_calculation.Group
def power_cost(group, new_group=None):
    if not group.auto_recalc or new_group and not new_group.auto_recalc:
        return None
    
    if not new_group:
        if group.default_power_fee:
            return (f"Tier {group.power} Power", int(group.default_power_fee) * 100, 'power')
        elif group.power_fee:
            return (f"Tier {group.power} Power (Custom Fee)", group.power_fee * 100, 'power_fee')
        return

    old_cost = group.power_fee if group.default_power_fee is None else int(group.default_power_fee)
    new_cost = new_group.power_fee if new_group.default_power_fee is None else int(new_group.default_power_fee)

    if old_cost == new_cost:
        return
    
    if new_group.power > group.power:
        if not group.power:
            label = f"Add Tier {new_group.power} Power"
        else:
            label = f"Upgrade Power to Tier {new_group.power}"
    elif group.power > new_group.power:
        if not new_group.power:
            label = "Remove Power"
        else:
            label = f"Downgrade Power to Tier {new_group.power}"
    else:
        if new_cost > old_cost:
            label = "Increase Custom Power Fee"
        else:
            label = "Decrease Custom Power Fee"
    
    return (label, (new_cost - old_cost) * 100, ('power', 'power_fee'))


Group.receipt_changes['tables'] = (table_cost, c.TABLE)
Group.receipt_changes['power'] = (power_cost, c.POWER)
Group.receipt_changes['power_fee'] = (power_cost, c.POWER)
