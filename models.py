from typing import Optional

from pydantic import BaseModel, Field, model_validator


class MealOption(BaseModel):
    title: str = Field(description="Catchy name of the dish")
    prep_time_minutes: int = Field(description="Estimated prep/cook time in minutes")
    estimated_calories_per_person: int = Field(
        description="Estimated calories per person, assuming the recipe serves 2 people"
    )
    ingredients_used: list[str] = Field(description="Ingredients identified from the image and used in this meal")
    missing_pantry_items: list[str] = Field(description="Basic staples needed like oil, salt, spices")
    instructions: list[str] = Field(
        description=(
            "Step-by-step cooking steps. Each step that uses an ingredient should state its quantity "
            "in grams or kilograms (e.g. '200g spinach', '1.5kg chicken'), or ml/L for liquids."
        )
    )


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
    indian_healthy_option: Optional[MealOption] = Field(
        default=None,
        description=(
            "Option 3: an Indian-cuisine dish, lighter/healthier than a typical restaurant version. "
            "Present only when food_detected is true."
        ),
    )
    recommended_ingredients: list[str] = Field(
        default_factory=list,
        description="Staple ingredients not currently visible that would be worth stocking up on next time.",
    )

    @model_validator(mode="after")
    def options_required_when_food_detected(self):
        if self.food_detected and (
            self.lazy_option is None or self.high_protein_option is None or self.indian_healthy_option is None
        ):
            raise ValueError(
                "food_detected is true, so lazy_option, high_protein_option, and indian_healthy_option must all be set"
            )
        return self
