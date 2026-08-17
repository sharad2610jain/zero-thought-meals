import os

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from history import list_history, save_generation, toggle_favorite
from meal_engine import STAPLE_OPTIONS, generate_meals
from shopping_list import build_shopping_list


def render_meal_option(badge_fn, label, meal):
    badge_fn(label)
    st.markdown(f"### {meal.title}")
    st.caption(f"⏱️ Prep time: {meal.prep_time_minutes} mins · 🔥 {meal.estimated_calories_per_person} kcal/person")
    st.write("**Ingredients Used:**", ", ".join(meal.ingredients_used))
    if meal.missing_pantry_items:
        st.write("**Assumed Staples:**", ", ".join(meal.missing_pantry_items))
    st.write("**Steps:**")
    for i, step in enumerate(meal.instructions, 1):
        st.write(f"{i}. {step}")


load_dotenv()

st.set_page_config(page_title="Zero-Thought Meal Engine", page_icon="🍳")
st.title("🍳 Zero-Thought Meal Engine")
st.write("Snap or upload a photo of your fridge/pantry to generate 3 instant meal choices.")

if not os.getenv("LITELLM_BASE_URL") or not os.getenv("LITELLM_API_KEY"):
    st.error("Missing LITELLM_BASE_URL or LITELLM_API_KEY environment variable.")
    st.stop()

col_camera, col_upload = st.columns(2)
with col_camera:
    camera_file = st.camera_input("Take a picture of open fridge or pantry")
with col_upload:
    uploaded_file = st.file_uploader("...or upload a photo", type=["jpg", "jpeg", "png"])

# If both are provided, the upload wins — it's the more deliberate action.
img_file = uploaded_file or camera_file

with st.expander("⚙️ Advanced options (optional)"):
    additional_files = st.file_uploader(
        "📦 Photos of what's inside containers/dabbas not visible in the main shot",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    extra_ingredients = st.text_area(
        "📝 Anything else you know you have (e.g. \"cooked dal, rice, leftover sabzi\")",
        value="",
    )

    st.write("🥗 Dietary preferences:")
    diet_col1, diet_col2 = st.columns([1, 2])
    with diet_col1:
        vegetarian = st.checkbox("Vegetarian (eggs/dairy OK)", value=False)
    with diet_col2:
        allergies = st.text_input("Allergies / ingredients to always avoid (comma-separated)", value="")

    st.write("🧂 Staples you actually have (uncheck anything you're out of):")
    staple_cols = st.columns(3)
    staple_checked = {}
    for i, staple in enumerate(STAPLE_OPTIONS):
        with staple_cols[i % 3]:
            staple_checked[staple] = st.checkbox(staple, value=True)

available_staples = [s for s, checked in staple_checked.items() if checked]
unavailable_staples = [s for s, checked in staple_checked.items() if not checked]

has_images = img_file or additional_files

generate_clicked = st.button("🍳 Generate meals", disabled=not has_images)

if generate_clicked:
    with st.spinner("Analyzing ingredients and generating zero-thought meals..."):
        try:
            images = []
            if img_file:
                images.append(Image.open(img_file))
            for extra_file in additional_files:
                images.append(Image.open(extra_file))

            data = generate_meals(
                images,
                extra_ingredients=extra_ingredients,
                available_staples=available_staples,
                unavailable_staples=unavailable_staples,
                vegetarian=vegetarian,
                allergies=allergies,
            )

            if not data.food_detected:
                st.warning("🤔 No food detected — try pointing the camera at your fridge or pantry shelf.")
            else:
                save_generation(data)

                st.subheader("🔍 Detected Ingredients")
                st.write(", ".join(data.ingredients_detected))

                st.divider()

                col1, col2, col3 = st.columns(3)

                with col1, st.container(border=True):
                    render_meal_option(st.success, "⚡ Option 1: Lazy Mode", data.lazy_option)

                with col2, st.container(border=True):
                    render_meal_option(st.info, "💪 Option 2: High Protein", data.high_protein_option)

                with col3, st.container(border=True):
                    render_meal_option(st.warning, "🌶️ Option 3: Indian & Healthy", data.indian_healthy_option)

                shopping_list = build_shopping_list(data)
                if shopping_list:
                    st.divider()
                    st.subheader("🛒 Shopping list")
                    st.caption("Staples these recipes need that you don't have, plus staples worth keeping stocked.")
                    st.code("\n".join(shopping_list), language=None)

        except Exception as e:
            st.error(f"Error processing image: {e}")

history_entries = list_history()
if history_entries:
    st.divider()
    st.subheader("📜 Past meals")
    for entry in history_entries:
        response = entry["response"]
        titles = ", ".join(
            option.title
            for option in (response.lazy_option, response.high_protein_option, response.indian_healthy_option)
            if option is not None
        )
        star = "⭐" if entry["favorite"] else "☆"
        with st.expander(f"{star} {entry['created_at']} — {titles}"):
            if st.button("Toggle favorite", key=f"favorite_{entry['id']}"):
                toggle_favorite(entry["id"])
                st.rerun()

            hist_col1, hist_col2, hist_col3 = st.columns(3)
            with hist_col1, st.container(border=True):
                render_meal_option(st.success, "⚡ Option 1: Lazy Mode", response.lazy_option)
            with hist_col2, st.container(border=True):
                render_meal_option(st.info, "💪 Option 2: High Protein", response.high_protein_option)
            with hist_col3, st.container(border=True):
                render_meal_option(st.warning, "🌶️ Option 3: Indian & Healthy", response.indian_healthy_option)
