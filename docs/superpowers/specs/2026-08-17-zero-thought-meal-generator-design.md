# Zero-Thought Meal Generator — Design

## Purpose

A portfolio piece: snap a photo of an open fridge/pantry, get two instant,
ready-to-cook meal ideas back (a "lazy mode" option and a "high protein"
option), with zero decision-making required from the user. Built as a
Streamlit app, deployable as a public demo link.

Source spec: user-authored implementation guide (Google Doc), adapted below
for the actual LLM backend available (see "Deviations from the original doc").

## Deviations from the original doc

The original doc assumed direct Gemini 2.5 Flash access via `google-genai`.
The user's available credential is a work-issued LiteLLM project token,
authorized for personal use, with access to exactly two models: **Claude
Sonnet 5** (chosen) and Claude Sonnet 4.6. This changes the "Brain" layer:

- LLM access goes through an **OpenAI-compatible client** (`openai` SDK)
  pointed at the LiteLLM proxy's `base_url`, not `google-genai`.
- Structured output uses **`instructor`** (patches the OpenAI client to
  retry until the response validates against a Pydantic model) instead of
  `response_schema`, since strict JSON-schema mode isn't guaranteed across
  every LiteLLM route.
- Model is **Claude Sonnet 5**, not Gemini 2.5 Flash. Claude supports image
  input via the same content-parts format LiteLLM expects, so the
  photo-to-meal-ideas flow is unaffected functionally.

## Prerequisites (external, not part of this build)

- LiteLLM proxy base URL — user needs to locate this before local testing.
- Exact model alias string registered for "Sonnet 5" on that proxy — may not
  literally be `sonnet-5`; user confirms once they have proxy access.

Both are read from env vars (see Configuration), so the code does not need
to change once these are known — only `.env` values do.

## Improvements adopted before implementation

Discussed and decided before writing the plan:

- **No food detected handling (adopted):** `MealResponse` gets a
  `food_detected: bool` field; meal options become optional and are only
  populated when food is detected. The UI shows a friendly message instead
  of a hallucinated meal when the photo has no visible food.
- **Image downscaling (adopted):** photos are resized to a max dimension
  before being sent to the model. Chosen threshold (1024px on the longest
  side) is at or above what vision-capable LLMs typically process
  internally anyway, so this should cut payload size/latency for
  full-resolution phone photos (often 3000px+) without a quality
  trade-off. `meal_engine.generate_meals` calls this itself, so it also
  applies to Streamlit's live camera capture, not just future manual
  photo uploads.
- **Stronger prompt constraints (adopted):** the instruction prompt sent
  with the image explicitly states the rules currently only implied by
  Pydantic field descriptions — don't invent ingredients not visible in
  the photo, `lazy_option` must be ≤10 min prep, `high_protein_option`
  must prioritize protein, and set `food_detected=false` (with no meal
  options) if nothing edible is visible. Models follow instructions in
  prompt text more reliably than schema docstrings alone.
- **Usage cap (deferred, not this build):** a per-session generation
  limit would get in the way of iterating during development/testing. Add
  it later, once the app is ready to go live publicly. See "Out of scope."

## Architecture

- **Frontend:** Streamlit, `st.camera_input` for capturing/uploading the
  fridge/pantry photo. Two-column results layout (lazy option / high
  protein option), same UX as the original doc.
- **Brain:** `openai.OpenAI(base_url=LITELLM_BASE_URL, api_key=LITELLM_API_KEY)`
  wrapped with `instructor.from_openai(...)`, calling `MODEL_NAME` with the
  photo (as an image content part) + a fixed instruction prompt.
- **Schema validation:** Pydantic models `MealOption` (title,
  prep_time_minutes, ingredients_used, missing_pantry_items, instructions
  — same as the original doc) and `MealResponse` (`food_detected: bool`,
  `ingredients_detected: list[str]`, `lazy_option: Optional[MealOption]`,
  `high_protein_option: Optional[MealOption]` — the two options are only
  populated when `food_detected` is true).
- **Hosting/Deployment:** GitHub (user's personal account, pushed later —
  out of scope for this build) + Streamlit Community Cloud. Documented as
  steps in the README; not executed as part of this work.

## Repo structure

```
zero-thought-meals/
  app.py                      # Streamlit UI only — no LLM logic
  meal_engine.py               # PROMPT, prepare_image(), generate_meals() -> MealResponse
  models.py                    # MealOption, MealResponse (Pydantic)
  tests/
    test_meal_engine.py        # unit tests, LLM call mocked
  requirements.txt
  .env.example
  .gitignore
  README.md
```

Rationale: `app.py` (Streamlit) is not meaningfully unit-testable, so the
only logic worth testing — prompt construction and response parsing — lives
in `meal_engine.py`, independent of the UI layer.

## Data flow

1. User captures/uploads a photo via `st.camera_input` in `app.py`.
2. `app.py` calls `meal_engine.generate_meals(image)`.
3. `generate_meals` calls `prepare_image(image)` to downscale it (max
   1024px on the longest side, preserving aspect ratio).
4. `generate_meals` builds an instructor-wrapped chat completion request
   (downscaled image + `PROMPT` instruction text), targeting
   `MealResponse` as the `response_model`, and calls the LiteLLM proxy.
5. `instructor` validates/retries until the response parses into a
   `MealResponse` instance (or raises after its retry budget).
6. `app.py` checks `data.food_detected`: if false, shows a friendly
   "no food detected" message; if true, renders `ingredients_detected`
   plus the two `MealOption` columns as in the original doc's UI code.

## Configuration

Env vars, loaded via `python-dotenv` locally and Streamlit secrets once
deployed:

- `LITELLM_BASE_URL`
- `LITELLM_API_KEY`
- `MODEL_NAME` (default placeholder, e.g. `"sonnet-5"` — user corrects to
  the real proxy alias once known)

Missing required env vars → `st.error(...)` + `st.stop()` in `app.py`,
matching the original doc's pattern for the missing-API-key case.

## Error handling

- Missing env vars at startup: `st.error` + `st.stop()`.
- LLM call or validation failure (including `instructor` exhausting
  retries): caught around the `generate_meals` call in `app.py`, shown via
  `st.error(f"Error processing image: {e}")`.

## Testing

- `tests/test_meal_engine.py`:
  - `prepare_image`: a larger-than-threshold image is resized so its
    longest side is ≤1024px with aspect ratio preserved; a
    smaller-than-threshold image is left unchanged.
  - `generate_meals` (mocked instructor/client call): sends the
    downscaled image + `PROMPT` content, and returns a `MealResponse`
    parsed from a sample mocked response — covering both a
    `food_detected=true` response (with populated options) and a
    `food_detected=false` response (options `None`).
- No tests for `app.py` — it's a thin Streamlit rendering layer with no
  independent logic once `generate_meals` is extracted.

## Out of scope for this build

- Actually pushing to GitHub / creating the remote repo (user handles this
  separately once ready).
- Deploying to Streamlit Community Cloud (documented in README as
  follow-up steps, not executed).
- Resolving the LiteLLM base URL / exact model alias (user prerequisite).
- Per-session/usage rate limiting — deferred until the app is ready to go
  live publicly, so it doesn't get in the way of dev-time testing.
