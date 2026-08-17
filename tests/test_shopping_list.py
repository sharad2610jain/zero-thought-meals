from models import MealOption, MealResponse
from shopping_list import build_shopping_list


def _option(missing_pantry_items):
    return MealOption(
        title="Test Dish",
        prep_time_minutes=10,
        estimated_calories_per_person=300,
        ingredients_used=["eggs"],
        missing_pantry_items=missing_pantry_items,
        instructions=["Do the thing with 100g of it"],
    )


def test_build_shopping_list_combines_and_dedupes_across_options():
    response = MealResponse(
        food_detected=True,
        ingredients_detected=["eggs"],
        lazy_option=_option(["Oil", "Salt"]),
        high_protein_option=_option(["salt", "Cumin"]),
        indian_healthy_option=_option(["Garam masala"]),
        recommended_ingredients=["Ginger", "oil"],
    )

    result = build_shopping_list(response)

    assert result == ["Oil", "Salt", "Cumin", "Garam masala", "Ginger"]


def test_build_shopping_list_returns_empty_when_no_food_detected():
    response = MealResponse(food_detected=False, ingredients_detected=[])

    assert build_shopping_list(response) == []


def test_build_shopping_list_ignores_blank_entries():
    response = MealResponse(
        food_detected=True,
        ingredients_detected=["eggs"],
        lazy_option=_option(["Oil", "  ", ""]),
        high_protein_option=_option([]),
        indian_healthy_option=_option(["Salt"]),
        recommended_ingredients=[],
    )

    assert build_shopping_list(response) == ["Oil", "Salt"]
