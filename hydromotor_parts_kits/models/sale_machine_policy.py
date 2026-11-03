"""Pure sale-machine policy, shared by ORM entry points (no elevated access)."""


def prepare_line_values(values, order_machine_id):
    result = dict(values)
    inherited = values.get('x_hm_use_order_machine', 'x_hm_parts_machine_id' not in values)
    if values.get('display_type'):
        inherited = False
        result['x_hm_parts_machine_id'] = False
    elif inherited:
        result['x_hm_parts_machine_id'] = order_machine_id or False
    result['x_hm_use_order_machine'] = bool(inherited)
    return result


def machine_link_error(order_company, order_customer, machine_company, machine_customer, retired):
    if order_company != machine_company:
        return 'company'
    if not order_customer or not machine_customer or order_customer != machine_customer:
        return 'customer'
    if retired:
        return 'retired'
    return None


def parts_history_state(state, ordered, delivered):
    """Commercial/delivery evidence, never an installation claim."""
    if state == 'cancel':
        return 'cancelled'
    if state in ('draft', 'sent'):
        return 'offered'
    if delivered < 0:
        return 'returned'
    if delivered > 0:
        return 'delivered' if delivered >= ordered else 'part_delivered'
    return 'sold'
