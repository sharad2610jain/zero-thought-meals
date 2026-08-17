from models import MealResponse


def build_shopping_list(response: MealResponse) -> list[str]:
    """Combine missing_pantry_items across all three options plus recommended_ingredients,
    deduped case-insensitively while preserving first-seen order and casing."""
    items = []
    seen = set()

    def add(raw_item):
        item = raw_item.strip()
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            items.append(item)

    for option in (response.lazy_option, response.high_protein_option, response.indian_healthy_option):
        if option is None:
            continue
        for item in option.missing_pantry_items:
            add(item)

    for item in response.recommended_ingredients:
        add(item)

    return items
