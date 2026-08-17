# Zero-Thought Meal Generator

[![Tests](https://github.com/sharad2610jain/zero-thought-meals/actions/workflows/tests.yml/badge.svg)](https://github.com/sharad2610jain/zero-thought-meals/actions/workflows/tests.yml)

Snap a photo of your fridge or pantry and get three instant, ready-to-cook
meal ideas — a lazy (≤10 min) option, a high-protein option, and a
health-conscious Indian option — with zero decision-making required.

## How it works

A Streamlit app captures one or more photos, sends them (plus optional
context) to Claude Sonnet 5 via a LiteLLM proxy with a structured-output
prompt (enforced by `instructor` + Pydantic), and renders three meal ideas
side by side — each with per-person calorie estimates and gram/kg
quantities in every step.

**Features:**
- 📷 Camera capture or file upload, plus optional extra photos for items
  hidden inside containers/dabbas
- 📝 A free-text note for anything a photo can't show (e.g. "leftover rice")
- 🧂 A staples checklist (oil, salt, common masalas) so the model only
  assumes what you actually confirm having, never guesses
- 🥗 Vegetarian toggle and a free-text allergy/avoid-list, enforced as hard
  constraints across all three options
- 🛒 A one-click copyable shopping list combining what each recipe needs
  with what's worth restocking
- 📜 Local history of past generations with a favorite toggle (see the
  persistence caveat below)
- 🔒 A per-session generation cap (default 5, override with
  `MAX_GENERATIONS_PER_SESSION`) so a public demo link can't run up an
  unbounded API bill

## Demo

![Demo](docs/demo.gif)

## Local setup

```bash
uv venv  # uses Python 3.12 per .python-version — instructor's type hints
         # require 3.10+, so don't let this fall back to an older system Python
uv pip install -r requirements.txt
cp .env.example .env
# edit .env: set LITELLM_BASE_URL, LITELLM_API_KEY, and MODEL_NAME
uv run streamlit run app.py
```

`LITELLM_BASE_URL` should point at your own LiteLLM proxy (or any
OpenAI-compatible endpoint) that has a Claude Sonnet model registered.
`MODEL_NAME` must match the exact model alias registered there, which is
often not the plain model name — check what's available with:

```bash
curl "$LITELLM_BASE_URL/v1/models" -H "Authorization: Bearer $LITELLM_API_KEY"
```

Open http://localhost:8501, allow camera access, and take a photo of your
fridge or pantry.

## Running tests

```bash
uv run pytest -v
```

## Deployment

1. Push this repo to GitHub under your personal account.
2. Connect the repo on [Streamlit Community Cloud](https://share.streamlit.io).
3. Set `LITELLM_BASE_URL`, `LITELLM_API_KEY`, and `MODEL_NAME` (and
   optionally `MAX_GENERATIONS_PER_SESSION`) under **Advanced Settings >
   Secrets**, in TOML format:
   ```toml
   LITELLM_BASE_URL = "https://your-proxy-url"
   LITELLM_API_KEY = "your-key"
   MODEL_NAME = "your-model-alias"
   ```
4. Deploy to get a public demo URL.

## Known follow-ups

- **History/favorites (`history.db`) is local-only.** It's a SQLite file on
  disk, gitignored, and works great when you run this yourself. Streamlit
  Community Cloud's filesystem is ephemeral — the moment the app restarts or
  redeploys there, this data is gone. If you want history to survive on the
  public deployment, swap `history.py`'s storage for a real hosted database
  (e.g. Supabase, Turso, or a Google Sheet) before relying on it there.
