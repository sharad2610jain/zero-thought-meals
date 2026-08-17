import pytest
from pydantic import ValidationError

from models import MealOption, MealResponse


def test_meal_option_holds_all_fields():
    option = MealOption(
        title="Fried Eggs",
        prep_time_minutes=5,
        estimated_calories_per_person=250,
        ingredients_used=["eggs"],
        missing_pantry_items=["oil", "salt"],
        instructions=["Crack 2 eggs (100g) into a hot pan", "Cook for 3 minutes"],
    )
    assert option.title == "Fried Eggs"
    assert option.prep_time_minutes == 5
    assert option.estimated_calories_per_person == 250
    assert option.ingredients_used == ["eggs"]
    assert option.missing_pantry_items == ["oil", "salt"]
    assert option.instructions == ["Crack 2 eggs (100g) into a hot pan", "Cook for 3 minutes"]


def test_meal_response_options_default_to_none():
    response = MealResponse(food_detected=False, ingredients_detected=[])
    assert response.lazy_option is None
    assert response.high_protein_option is None
    assert response.indian_healthy_option is None
    assert response.recommended_ingredients == []


def test_meal_response_requires_food_detected_field():
    with pytest.raises(ValidationError):
        MealResponse(ingredients_detected=[])


def test_meal_response_rejects_food_detected_without_options():
    with pytest.raises(ValidationError):
        MealResponse(food_detected=True, ingredients_detected=["eggs"])


def _sample_option(title):
    return MealOption(
        title=title,
        prep_time_minutes=10,
        estimated_calories_per_person=300,
        ingredients_used=["eggs"],
        missing_pantry_items=["oil", "salt"],
        instructions=["Do the thing with 200g of it"],
    )


def test_meal_response_rejects_food_detected_missing_only_indian_option():
    with pytest.raises(ValidationError):
        MealResponse(
            food_detected=True,
            ingredients_detected=["eggs"],
            lazy_option=_sample_option("Lazy Eggs"),
            high_protein_option=_sample_option("Protein Eggs"),
        )


def test_meal_response_accepts_food_detected_with_all_three_options():
    response = MealResponse(
        food_detected=True,
        ingredients_detected=["eggs"],
        lazy_option=_sample_option("Lazy Eggs"),
        high_protein_option=_sample_option("Protein Eggs"),
        indian_healthy_option=_sample_option("Egg Bhurji"),
        recommended_ingredients=["spinach", "paneer"],
    )
    assert response.indian_healthy_option.title == "Egg Bhurji"
    assert response.recommended_ingredients == ["spinach", "paneer"]
