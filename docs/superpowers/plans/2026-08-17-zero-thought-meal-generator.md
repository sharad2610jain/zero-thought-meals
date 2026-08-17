# Zero-Thought Meal Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit app that takes a fridge/pantry photo and returns two ready-to-cook meal ideas (a ≤10-minute "lazy" option and a protein-focused option), generated via Claude Sonnet 5 through a LiteLLM proxy.

**Architecture:** Three-file split — `models.py` (Pydantic schemas), `meal_engine.py` (image prep + LLM call, fully unit-testable, no Streamlit dependency), `app.py` (thin Streamlit UI that calls `meal_engine.generate_meals`). Structured output is enforced via `instructor` wrapping an OpenAI-compatible client pointed at the LiteLLM proxy.

**Tech Stack:** Python (managed with `uv`), Streamlit, `openai` SDK, `instructor`, Pydantic, Pillow, `python-dotenv`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-08-17-zero-thought-meal-generator-design.md`

## Global Constraints

- Use `uv` for virtualenv + dependency management, not raw `pip`/`venv` (per user preference).
- LLM backend is Claude Sonnet 5 via a LiteLLM proxy — never `google-genai`/Gemini (credential doesn't have Gemini access).
- Structured output uses `instructor`, not `response_schema`/`response_mime_type`.
- `MAX_IMAGE_DIMENSION = 1024` (px, longest side) for all images sent to the LLM — do not send full-resolution camera captures.
- `MealResponse.lazy_option` and `MealResponse.high_protein_option` are `Optional[MealOption]`, populated only when `food_detected` is `True`.
- Do NOT implement usage/rate limiting in this build — explicitly deferred (see spec's "Out of scope").
- Do NOT push to GitHub or deploy to Streamlit Community Cloud in this build — explicitly out of scope (user handles later).
- Do NOT hardcode `LITELLM_BASE_URL`, `LITELLM_API_KEY`, or the real model alias anywhere — read from env vars only. Real values for these three are an external prerequisite the user supplies in `.env`; use `"sonnet-5"` as the `MODEL_NAME` default in code.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `tests/` (empty directory, will hold test modules from later tasks)

**Interfaces:**
- Consumes: nothing (first task)
- Produces: an installed virtualenv (`.venv/`) with all dependencies later tasks need; `.env.example` documents the three required env vars.

- [ ] **Step 1: Create `requirements.txt`**

```
streamlit
openai
instructor
pydantic
pillow
python-dotenv
pytest
```

- [ ] **Step 2: Create the virtualenv and install dependencies**

Run: `cd /Users/sharad.jain/Documents/GitHub/zero-thought-meals && uv venv && uv pip install -r requirements.txt`
Expected: completes with no errors, `.venv/` directory created.

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
```

- [ ] **Step 4: Create `.env.example`**

```
LITELLM_BASE_URL=https://your-litellm-proxy-url
LITELLM_API_KEY=your-litellm-project-token
MODEL_NAME=sonnet-5
```

- [ ] **Step 5: Create empty `tests/` directory**

Run: `mkdir -p tests`

- [ ] **Step 6: Verify the environment**

Run: `uv run python -c "import streamlit, openai, instructor, pydantic, PIL, dotenv, pytest; print('ok')"`
Expected: prints `ok` with no import errors.

- [ ] **Step 7: Commit**

```bash
touch tests/.gitkeep
git add requirements.txt .gitignore .env.example tests/.gitkeep
git commit -m "chore: scaffold project with uv, requirements, and env template"
```

---

## Task 2: Pydantic Schemas (`models.py`)

**Files:**
- Create: `models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `MealOption(title: str, prep_time_minutes: int, ingredients_used: list[str], missing_pantry_items: list[str], instructions: list[str])`
  - `MealResponse(food_detected: bool, ingredients_detected: list[str], lazy_option: Optional[MealOption] = None, high_protein_option: Optional[MealOption] = None)`

- [ ] **Step 1: Write the failing tests**

`tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from models import MealOption, MealResponse


def test_meal_option_holds_all_fields():
    option = MealOption(
        title="Fried Eggs",
        prep_time_minutes=5,
        ingredients_used=["eggs"],
        missing_pantry_items=["oil", "salt"],
        instructions=["Crack eggs into a hot pan", "Cook for 3 minutes"],
    )
    assert option.title == "Fried Eggs"
    assert option.prep_time_minutes == 5
    assert option.ingredients_used == ["eggs"]
    assert option.missing_pantry_items == ["oil", "salt"]
    assert option.instructions == ["Crack eggs into a hot pan", "Cook for 3 minutes"]


def test_meal_response_options_default_to_none():
    response = MealResponse(food_detected=False, ingredients_detected=[])
    assert response.lazy_option is None
    assert response.high_protein_option is None


def test_meal_response_requires_food_detected_field():
    with pytest.raises(ValidationError):
        MealResponse(ingredients_detected=[])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Write the implementation**

`models.py`:

```python
from typing import Optional

from pydantic import BaseModel, Field


class MealOption(BaseModel):
    title: str = Field(description="Catchy name of the dish")
    prep_time_minutes: int = Field(description="Estimated prep/cook time in minutes")
    ingredients_used: list[str] = Field(description="Ingredients identified from the image and used in this meal")
    missing_pantry_items: list[str] = Field(description="Basic staples needed like oil, salt, spices")
    instructions: list[str] = Field(description="Step-by-step cooking steps")


class MealResponse(BaseModel):
    food_detected: bool = Field(description="Whether any recognizable food/ingredients are visible in the image")
    ingredients_detected: list[str] = Field(description="All visible ingredients in the image")
    lazy_option: Optional[MealOption] = Field(
        default=None,
        description="Option 1: max 10 mins prep, absolute minimum effort. Present only when food_detected is true.",
    )
    high_protein_option: Optional[MealOption] = Field(
        default=None,
        description="Option 2: focus on protein and clean nutrition. Present only when food_detected is true.",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat: add MealOption and MealResponse schemas"
```

---

## Task 3: Image Downscaling (`meal_engine.prepare_image`)

**Files:**
- Create: `meal_engine.py`
- Create: `tests/test_meal_engine.py`

**Interfaces:**
- Consumes: `PIL.Image.Image`
- Produces: `MAX_IMAGE_DIMENSION: int = 1024`; `prepare_image(image: Image.Image) -> Image.Image`

- [ ] **Step 1: Write the failing tests**

`tests/test_meal_engine.py`:

```python
from PIL import Image

from meal_engine import MAX_IMAGE_DIMENSION, prepare_image


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_meal_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'meal_engine'`

- [ ] **Step 3: Write the implementation**

`meal_engine.py`:

```python
from PIL import Image

MAX_IMAGE_DIMENSION = 1024


def prepare_image(image: Image.Image) -> Image.Image:
    if max(image.size) <= MAX_IMAGE_DIMENSION:
        return image
    resized = image.copy()
    resized.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
    return resized
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_meal_engine.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add meal_engine.py tests/test_meal_engine.py
git commit -m "feat: add image downscaling before LLM calls"
```

---

## Task 4: LLM Call (`meal_engine.generate_meals`)

**Files:**
- Modify: `meal_engine.py`
- Modify: `tests/test_meal_engine.py`

**Interfaces:**
- Consumes: `models.MealResponse`, `models.MealOption` (Task 2); `prepare_image`, `MAX_IMAGE_DIMENSION` (Task 3)
- Produces:
  - `PROMPT: str`
  - `get_client() -> instructor.Instructor` (reads `LITELLM_BASE_URL`, `LITELLM_API_KEY` from `os.environ`)
  - `generate_meals(image: Image.Image, client: Optional[instructor.Instructor] = None) -> MealResponse`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_meal_engine.py`:

```python
from unittest.mock import MagicMock

from models import MealOption, MealResponse
from meal_engine import PROMPT, generate_meals


def test_generate_meals_returns_parsed_response_when_food_detected():
    fake_response = MealResponse(
        food_detected=True,
        ingredients_detected=["eggs", "spinach"],
        lazy_option=MealOption(
            title="Fried Eggs",
            prep_time_minutes=5,
            ingredients_used=["eggs"],
            missing_pantry_items=["oil", "salt"],
            instructions=["Crack eggs into a hot pan", "Cook for 3 minutes"],
        ),
        high_protein_option=MealOption(
            title="Spinach Omelette",
            prep_time_minutes=8,
            ingredients_used=["eggs", "spinach"],
            missing_pantry_items=["oil"],
            instructions=["Whisk eggs", "Add spinach", "Cook through"],
        ),
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    result = generate_meals(image, client=mock_client)

    assert result == fake_response
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_model"] is MealResponse
    content = call_kwargs["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": PROMPT}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_generate_meals_returns_response_with_no_options_when_no_food_detected():
    fake_response = MealResponse(food_detected=False, ingredients_detected=[])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response

    image = Image.new("RGB", (200, 200), color="white")
    result = generate_meals(image, client=mock_client)

    assert result.food_detected is False
    assert result.lazy_option is None
    assert result.high_protein_option is None
```

Add `from PIL import Image` to the top of `tests/test_meal_engine.py` if not already imported from Task 3.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_meal_engine.py -v`
Expected: FAIL with `ImportError: cannot import name 'PROMPT' from 'meal_engine'`

- [ ] **Step 3: Write the implementation**

Replace `meal_engine.py` with:

```python
import base64
import os
from io import BytesIO
from typing import Optional

import instructor
from openai import OpenAI
from PIL import Image

from models import MealResponse

MAX_IMAGE_DIMENSION = 1024

PROMPT = """You are a meal-generation assistant analyzing a photo of an open fridge or pantry.

Identify every visible food item in the photo and list it in ingredients_detected.
Only use ingredients you can actually see in the photo. Never invent ingredients that are not visible.

If no recognizable food items are visible, set food_detected to false, leave ingredients_detected empty, and leave lazy_option and high_protein_option unset.

If food items are visible, set food_detected to true and generate exactly two meal ideas using only the visible ingredients (plus basic pantry staples like oil, salt, and spices, listed under missing_pantry_items):
1. lazy_option: the absolute minimum-effort meal. prep_time_minutes must be 10 or less.
2. high_protein_option: a meal that prioritizes protein content and clean nutrition.

For both options, provide clear, numbered, step-by-step instructions."""


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


def generate_meals(image: Image.Image, client: Optional[instructor.Instructor] = None) -> MealResponse:
    client = client or get_client()
    resized = prepare_image(image)
    data_url = _image_to_data_url(resized)
    model_name = os.environ.get("MODEL_NAME", "sonnet-5")

    return client.chat.completions.create(
        model=model_name,
        response_model=MealResponse,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_meal_engine.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add meal_engine.py tests/test_meal_engine.py
git commit -m "feat: call LiteLLM proxy via instructor for structured meal generation"
```

---

## Task 5: Streamlit UI (`app.py`)

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `meal_engine.generate_meals` (Task 4); `models.MealResponse`, `models.MealOption` field names (Task 2)
- Produces: nothing (terminal, user-facing entrypoint)

- [ ] **Step 1: Write `app.py`**

```python
import os

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from meal_engine import generate_meals

load_dotenv()

st.set_page_config(page_title="Zero-Thought Meal Engine", page_icon="🍳")
st.title("🍳 Zero-Thought Meal Engine")
st.write("Snap a photo of your fridge/pantry to generate 2 instant meal choices.")

if not os.getenv("LITELLM_BASE_URL") or not os.getenv("LITELLM_API_KEY"):
    st.error("Missing LITELLM_BASE_URL or LITELLM_API_KEY environment variable.")
    st.stop()

img_file = st.camera_input("Take a picture of open fridge or pantry")

if img_file:
    img = Image.open(img_file)

    with st.spinner("Analyzing ingredients and generating zero-thought meals..."):
        try:
            data = generate_meals(img)

            if not data.food_detected:
                st.warning("🤔 No food detected — try pointing the camera at your fridge or pantry shelf.")
            else:
                st.subheader("🔍 Detected Ingredients")
                st.write(", ".join(data.ingredients_detected))

                st.divider()

                col1, col2 = st.columns(2)

                with col1:
                    st.success("⚡ Option 1: Lazy Mode")
                    meal1 = data.lazy_option
                    st.markdown(f"### {meal1.title}")
                    st.caption(f"⏱️ Prep time: {meal1.prep_time_minutes} mins")
                    st.write("**Ingredients Used:**", ", ".join(meal1.ingredients_used))
                    if meal1.missing_pantry_items:
                        st.write("**Assumed Staples:**", ", ".join(meal1.missing_pantry_items))
                    st.write("**Steps:**")
                    for i, step in enumerate(meal1.instructions, 1):
                        st.write(f"{i}. {step}")

                with col2:
                    st.info("💪 Option 2: High Protein")
                    meal2 = data.high_protein_option
                    st.markdown(f"### {meal2.title}")
                    st.caption(f"⏱️ Prep time: {meal2.prep_time_minutes} mins")
                    st.write("**Ingredients Used:**", ", ".join(meal2.ingredients_used))
                    if meal2.missing_pantry_items:
                        st.write("**Assumed Staples:**", ", ".join(meal2.missing_pantry_items))
                    st.write("**Steps:**")
                    for i, step in enumerate(meal2.instructions, 1):
                        st.write(f"{i}. {step}")

        except Exception as e:
            st.error(f"Error processing image: {e}")
```

- [ ] **Step 2: Verify the missing-env-var path (no real LiteLLM credentials needed)**

**Known plan defect (found during execution, see ledger):** the curl-based check
below cannot work for any Streamlit app — Streamlit serves a client-rendered
SPA shell over plain HTTP, so `st.error`/`st.stop` output only appears after
the frontend JS connects over WebSocket, never in the raw HTML curl fetches.
If reusing this plan as a template, replace this step with a `runpy`-based
direct interception instead: run `app.py`'s top-level code via
`runpy.run_path("app.py", run_name="__main__")` with `LITELLM_BASE_URL`/
`LITELLM_API_KEY` unset, monkeypatching `st.error`/`st.stop`/`st.camera_input`
to record calls, and assert `st.error` fires with the expected message,
`st.stop` follows, and `st.camera_input` is never reached.

Run: `cd /Users/sharad.jain/Documents/GitHub/zero-thought-meals && uv run streamlit run app.py --server.headless true &`
Then: `sleep 3 && curl -s http://localhost:8501 | grep -o "Missing LITELLM"` (with no `.env` file present)
Expected: prints `Missing LITELLM`, confirming the app correctly halts without credentials. Stop the background process afterward (`kill %1` or the equivalent job).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Streamlit UI for zero-thought meal generation"
```

- [ ] **Step 4: Note for the user — full happy-path verification**

Once `.env` is filled in with a real `LITELLM_BASE_URL`, `LITELLM_API_KEY`, and confirmed `MODEL_NAME`, run `uv run streamlit run app.py`, open http://localhost:8501, and verify: (a) a photo of an empty/food-free surface shows the "No food detected" warning, (b) a photo of a stocked fridge/pantry shows detected ingredients plus both meal columns rendered correctly. This step is external to this plan (blocked on the LiteLLM base URL prerequisite) and is not required to consider Task 5 complete.

---

## Task 6: README and Final Housekeeping

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: all prior tasks (documents how to run what they built)
- Produces: nothing (terminal, documentation only)

- [ ] **Step 1: Write `README.md`**

```markdown
# Zero-Thought Meal Generator

Snap a photo of your fridge or pantry and get two instant, ready-to-cook
meal ideas — a lazy (≤10 min) option and a high-protein option — with zero
decision-making required.

## How it works

A Streamlit app captures a photo, sends it to Claude Sonnet 5 via a LiteLLM
proxy with a structured-output prompt (enforced by `instructor` + Pydantic),
and renders the two meal ideas side by side.

## Local setup

```bash
uv venv
uv pip install -r requirements.txt
cp .env.example .env
# edit .env: set LITELLM_BASE_URL, LITELLM_API_KEY, and MODEL_NAME
uv run streamlit run app.py
```

Open http://localhost:8501, allow camera access, and take a photo of your
fridge or pantry.

## Running tests

```bash
uv run pytest -v
```

## Deployment (not yet done)

1. Push this repo to GitHub under your personal account.
2. Connect the repo on [Streamlit Community Cloud](https://share.streamlit.io).
3. Set `LITELLM_BASE_URL`, `LITELLM_API_KEY`, and `MODEL_NAME` under
   **Advanced Settings > Secrets**.
4. Deploy to get a public demo URL.

## Known follow-ups

- No per-session usage cap yet — add one before sharing the public link
  widely, since every generation call spends against the LiteLLM project
  token.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, testing, and deployment instructions"
```
