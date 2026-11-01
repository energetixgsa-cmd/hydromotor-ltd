"""Bounded-batch orchestration; the service remains the assembly authority."""


def implicit_exceptions(batches, catalog_code, assembly_product, matches, empty_matches):
    """IDs whose resolved value differs from the empty-value match result.

    The caller supplies only accessible, non-explicit, marker-bearing kits.
    Missing/malformed markers therefore need no special domain or full kit scan.
    Cache only inside this search, by exact code and kit company: never across
    users, contexts or transactions. Product eligibility stays dynamic.
    """
    resolved = {}
    exceptions = []
    for batch in batches:
        for kit in batch:
            code = catalog_code(kit)
            if not code:
                continue
            key = (code, kit.x_company_id.id)
            if key not in resolved:
                resolved[key] = matches(assembly_product(kit))
            if resolved[key] != empty_matches:
                exceptions.append(kit.id)
    return exceptions
