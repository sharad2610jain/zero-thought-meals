import base64
import os
from io import BytesIO
from typing import Optional

import instructor
from openai import OpenAI
from PIL import Image

from models import MealResponse

MAX_IMAGE_DIMENSION = 1024

STAPLE_OPTIONS = [
    "Cooking oil",
    "Salt",
    "Black pepper",
    "Turmeric",
    "Cumin (seeds or powder)",
    "Coriander powder",
    "Garam masala",
    "Chili powder",
    "Mustard seeds",
]

PROMPT = """You are a meal-generation assistant analyzing photo(s) of an open fridge or pantry.

You may receive more than one photo: typically one overview shot, plus optional close-up photos of items that were inside opaque containers, dabbas, or baskets in the overview shot. Treat every photo as showing part of the same fridge/pantry — combine what you see across all of them into a single ingredients_detected list, without duplicates. You may also receive a line of text listing ingredients the user has manually confirmed are available (e.g. because they're sealed in a container no photo could show) — add those to ingredients_detected too.

Identify every visible food item across all provided photos, plus any manually confirmed ingredients from the user's text note, and list them in ingredients_detected.
Only use ingredients you can actually see in a photo, or that the user explicitly confirmed in their text note. Never invent ingredients that are neither visible nor confirmed.

Household context: the user is on a weight-loss journey, but is the only cook in the household and prepares one shared meal for both themselves and their spouse, who is not dieting and wants genuinely tasty food. Never suggest cooking two separate dishes. Every option should be healthy enough to support weight loss (balanced portions, minimal added oil/sugar/ghee, favor lean protein and vegetables) while still being satisfying enough for a non-dieting eater to enjoy. A dish that sits right on the edge of "indulgent" is fine occasionally — just don't default to a heavier version when a lighter one works just as well.

Equipment available: stovetop, air fryer, and microwave. There is no oven — never write instructions that require baking or an oven.

If no recognizable food items are visible, set food_detected to false, leave ingredients_detected and recommended_ingredients empty, and leave lazy_option, high_protein_option, and indian_healthy_option unset.

The user will separately tell you exactly which common staples (oil, salt, spices/masalas) they currently have at home — do not assume any staple is available beyond what they confirm. For missing_pantry_items, list only staples the recipe needs that are NOT in their confirmed list. If a staple they confirmed they don't have is essential to a dish, either pick a different dish/technique that avoids it, or list it in missing_pantry_items so they know to buy it.

If food items are visible, set food_detected to true, populate ingredients_detected, and generate exactly three meal ideas using only the visible ingredients plus the confirmed staples:
1. lazy_option: the absolute minimum-effort meal. prep_time_minutes must be 10 or less.
2. high_protein_option: a meal that prioritizes protein content and clean nutrition.
3. indian_healthy_option: an Indian-cuisine dish using only the confirmed staples/masalas (never assume unconfirmed ones). Make it lighter than a typical restaurant version (less oil/ghee, no deep-frying) while still tasting authentic.

Assume every recipe serves 2 people (the user and their spouse). For each option, estimate estimated_calories_per_person as the calories for one person's serving, not the whole dish.

For all three options, give clear, numbered, step-by-step instructions using only stovetop, air fryer, and/or microwave techniques — never an oven. Every step that uses an ingredient must state its quantity in grams or kilograms (e.g. "200g spinach", "1.5kg chicken"), or ml/L for liquids — never vague amounts like "a handful" or "some".

Then populate recommended_ingredients with 3-6 ingredients not currently visible in the photo that would be worth keeping stocked at home — general staples that add variety across all three meal styles above (not just Indian-specific), especially anything you found yourself listing repeatedly under missing_pantry_items.

The user may also specify dietary constraints (e.g. vegetarian) or allergies/ingredients to avoid. Treat these as hard constraints: never violate them in any option, regardless of what's visible in a photo — if a visible ingredient conflicts with a stated constraint, simply don't use it in any of the three options."""


def prepare_image(image: Image.Image) -> Image.Image:
    if max(image.size) <= MAX_IMAGE_DIMENSION:
        return image
    resized = image.copy()
    resized.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
    return resized


def _image_to_data_url(image: Image.Image) -> str:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def get_client() -> instructor.Instructor:
    return instructor.from_openai(
        OpenAI(
            base_url=os.environ["LITELLM_BASE_URL"],
            api_key=os.environ["LITELLM_API_KEY"],
        )
    )


def generate_meals(
    images: list[Image.Image],
    extra_ingredients: str = "",
    available_staples: Optional[list[str]] = None,
    unavailable_staples: Optional[list[str]] = None,
    vegetarian: bool = False,
    allergies: str = "",
    client: Optional[instructor.Instructor] = None,
) -> MealResponse:
    client = client or get_client()
    model_name = os.environ.get("MODEL_NAME", "sonnet-5")

    content = [{"type": "text", "text": PROMPT}]

    available_staples = available_staples or []
    unavailable_staples = unavailable_staples or []
    if available_staples or unavailable_staples:
        staple_lines = []
        if available_staples:
            staple_lines.append(f"Confirmed AVAILABLE staples: {', '.join(available_staples)}.")
        if unavailable_staples:
            staple_lines.append(
                f"Confirmed NOT available (do not assume these, do not use them uncredited): {', '.join(unavailable_staples)}."
            )
        content.append({"type": "text", "text": " ".join(staple_lines)})

    dietary_lines = []
    if vegetarian:
        dietary_lines.append("The user is vegetarian: no meat, poultry, or fish in any option. Eggs and dairy are fine.")
    if allergies.strip():
        dietary_lines.append(f"The user must avoid these (allergy/preference), in every option: {allergies.strip()}.")
    if dietary_lines:
        content.append({"type": "text", "text": " ".join(dietary_lines)})

    if extra_ingredients.strip():
        content.append(
            {
                "type": "text",
                "text": f"The user also manually confirmed these additional ingredients are available: {extra_ingredients.strip()}",
            }
        )
    for image in images:
        data_url = _image_to_data_url(prepare_image(image))
        content.append({"type": "image_url", "image_url": {"url": data_url}})

    return client.chat.completions.create(
        model=model_name,
        response_model=MealResponse,
        messages=[{"role": "user", "content": content}],
    )
