from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from typing import List

# --- Importy wg nowej architektury aikcal-app v3.0 ---
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sql_models import User
from app.schemas.all_schemas import DaySummary
from app.crud import crud_base as crud  # Importujemy jako crud, aby zachować logikę wywołań (get_meals_by_date itp.)
from app.core import utils # Zakładamy przeniesienie utils do głównego katalogu app lub app.core

router = APIRouter()

@router.get("/{target_date}", response_model=DaySummary)
def get_daily_summary(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pobiera pełne podsumowanie danych z wybranego dnia, wzbogacając dane do edycji."""
    
    # Logika zachowana bez zmian, korzystająca z zaimportowanego modułu crud
    meals = crud.get_meals_by_date(db, user_id=current_user.id, target_date=target_date)
    workouts = crud.get_workouts_by_date(db, user_id=current_user.id, target_date=target_date)
    water_entries = crud.get_water_entries_by_date(db, user_id=current_user.id, target_date=target_date)

    # --- POCZĄTEK NOWEJ LOGIKI: WZBOGACANIE DANYCH ---
    for meal in meals:
        for entry in meal.entries:
            if entry.deconstruction_details:
                enriched_details = []
                for ingredient_detail in entry.deconstruction_details:
                    # Szukamy produktu w naszej bazie, aby pobrać jego wartości bazowe
                    product = crud.get_product_by_name(db, name=ingredient_detail.get("name"))
                    if product:
                        # Kopiujemy istniejące dane i dodajemy kluczową, brakującą informację
                        new_detail = ingredient_detail.copy()
                        new_detail["nutrients_per_100g"] = product.nutrients
                        enriched_details.append(new_detail)
                entry.deconstruction_details = enriched_details
    # --- KONIEC NOWEJ LOGIKI ---

    calories_consumed = sum(e.calories for m in meals for e in m.entries)
    calories_burned = sum(w.calories_burned for w in workouts)
    water_consumed = sum(w.amount for w in water_entries)
    
    effective_calorie_goal = current_user.calorie_goal or 0
    if current_user.add_workout_calories_to_goal:
        effective_calorie_goal += calories_burned

    goal_date = utils.calculate_goal_achievement_date(current_user)

    # Użycie nowego schematu DaySummary zamiast starego schemas.DailySummary
    summary = DaySummary(
        date=target_date,
        calories_consumed=calories_consumed,
        protein_consumed=sum(e.protein for m in meals for e in m.entries),
        fat_consumed=sum(e.fat for m in meals for e in m.entries),
        carbs_consumed=sum(e.carbs for m in meals for e in m.entries),
        water_consumed=water_consumed,
        calories_burned=calories_burned,
        total_calories_burned_today=calories_burned,
        calorie_goal=effective_calorie_goal,
        protein_goal=current_user.protein_goal or 0,
        fat_goal=current_user.fat_goal or 0,
        carb_goal=current_user.carb_goal or 0,
        water_goal=current_user.water_goal or 0,
        meals=meals,
        water_entries=water_entries,
        workouts=workouts,
        goal_achievement_date=goal_date
    )
    return summary