def description_without_reference(description, reference):
    """Remove only Odoo's exact leading code; never strip arbitrary brackets."""
    if not description or not reference:
        return description
    prefix = f"[{reference}] "
    return description[len(prefix):] if description.startswith(prefix) else description
