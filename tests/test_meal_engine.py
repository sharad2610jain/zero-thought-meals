import base64
from io import BytesIO
from unittest.mock import MagicMock

from PIL import Image

from meal_engine import MAX_IMAGE_DIMENSION, PROMPT, generate_meals, prepare_image
from models import MealOption, MealResponse


def test_prepare_image_downscales_large_image_preserving_aspect_ratio():
    large = Image.new("RGB", (3000, 1500), color="white")
    resized = prepare_image(large)
    assert max(resized.size) == MAX_IMAGE_DIMENSION
    original_ratio = 3000 / 1500
    resized_ratio = resized.size[0] / resized.size[1]
    assert abs(original_ratio - resized_ratio) < 0.01


def test_prepare_image_leaves_small_image_unchanged():
    small = Image.new("RGB", (800, 600), color="white")
    resized = prepare_image(small)
    assert resized.size == (800, 600)


def test_generate_meals_returns_parsed_response_when_food_detected():
    fake_response = MealResponse(
        food_detected=True,
        ingredients_detected=["eggs", "spinach"],
        lazy_option=MealOption(
            title="Fried Eggs",
            prep_time_minutes=5,
            estimated_calories_per_person=220,
            ingredients_used=["eggs"],
            missing_pantry_items=["oil", "salt"],
            instructions=["Crack 2 eggs (100g) into a hot pan", "Cook for 3 minutes"],
        ),
        high_protein_option=MealOption(
            title="Spinach Omelette",
            prep_time_minutes=8,
            estimated_calories_per_person=280,
            ingredients_used=["eggs", "spinach"],
            missing_pantry_items=["oil"],
            instructions=["Whisk 3 eggs (150g)", "Add 50g spinach", "Cook through"],
        ),
        indian_healthy_option=MealOption(
            title="Egg Bhurji",
            prep_time_minutes=12,
            estimated_calories_per_person=260,
            ingredients_used=["eggs", "spinach"],
            missing_pantry_items=["oil", "turmeric", "cumin"],
            instructions=["Saute 50g spinach with spices", "Add 3 whisked eggs (150g)", "Cook through"],
        ),
        recommended_ingredients=["paneer", "yogurt"],
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    result = generate_meals([image], client=mock_client)

    assert result == fake_response
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_model"] is MealResponse
    assert call_kwargs["model"] == "sonnet-5"
    content = call_kwargs["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": PROMPT}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_generate_meals_returns_response_with_no_options_when_no_food_detected():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    result = generate_meals([image], client=mock_client)

    assert result.food_detected is False
    assert result.lazy_option is None
    assert result.high_protein_option is None
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "sonnet-5"


def test_generate_meals_sends_downscaled_image():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    large_image = Image.new("RGB", (3000, 1500), color="white")
    generate_meals([large_image], client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    data_url = content[1]["image_url"]["url"]
    encoded = data_url.split(",", 1)[1]
    sent_image = Image.open(BytesIO(base64.b64decode(encoded)))
    assert max(sent_image.size) == MAX_IMAGE_DIMENSION


def test_generate_meals_sends_all_provided_images():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    main_image = Image.new("RGB", (200, 200), color="white")
    container_image_1 = Image.new("RGB", (100, 100), color="red")
    container_image_2 = Image.new("RGB", (100, 100), color="blue")
    generate_meals([main_image, container_image_1, container_image_2], client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    image_blocks = [block for block in content if block["type"] == "image_url"]
    assert len(image_blocks) == 3


def test_generate_meals_includes_extra_ingredients_text_when_provided():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    generate_meals([image], extra_ingredients="cooked dal, rice", client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    text_blocks = [block["text"] for block in content if block["type"] == "text"]
    assert any("cooked dal, rice" in text for text in text_blocks)


def test_generate_meals_omits_extra_ingredients_block_when_blank():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    generate_meals([image], extra_ingredients="   ", client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    text_blocks = [block for block in content if block["type"] == "text"]
    assert len(text_blocks) == 1


def test_generate_meals_includes_staple_availability_when_provided():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    generate_meals(
        [image],
        available_staples=["Salt", "Cooking oil"],
        unavailable_staples=["Garam masala"],
        client=mock_client,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    text_blocks = [block["text"] for block in content if block["type"] == "text"]
    assert any("Salt, Cooking oil" in text and "AVAILABLE" in text for text in text_blocks)
    assert any("Garam masala" in text and "NOT available" in text for text in text_blocks)


def test_generate_meals_omits_staple_block_when_no_staples_given():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    generate_meals([image], client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    text_blocks = [block for block in content if block["type"] == "text"]
    assert len(text_blocks) == 1


def test_generate_meals_includes_vegetarian_constraint_when_set():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    generate_meals([image], vegetarian=True, client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    text_blocks = [block["text"] for block in content if block["type"] == "text"]
    assert any("vegetarian" in text.lower() for text in text_blocks)


def test_generate_meals_includes_allergies_when_provided():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    generate_meals([image], allergies="peanuts, shellfish", client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    text_blocks = [block["text"] for block in content if block["type"] == "text"]
    assert any("peanuts, shellfish" in text for text in text_blocks)


def test_generate_meals_omits_dietary_block_when_neither_set():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    generate_meals([image], vegetarian=False, allergies="", client=mock_client)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    text_blocks = [block for block in content if block["type"] == "text"]
    assert len(text_blocks) == 1
