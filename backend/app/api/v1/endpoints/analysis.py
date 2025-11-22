from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
import json

from app.core.database import get_db
from app.api import deps
from app.api.deps import get_current_user
from app.crud import crud_base as crud
from app.models import sql_models as models
from app.schemas import all_schemas as schemas
# Importujemy poprawiony serwis AI (z funkcją analyze_meal_text)
from app.services import legacy_analyzer as ai_analyzer

router = APIRouter()

# --- GŁÓWNY ENDPOINT DO ANALIZY POSIŁKU ---
@router.post("/meal", response_model=schemas.AnalysisResponse)
async def analyze_meal_endpoint(
    request: schemas.AnalysisRequest,
):
    """
    Analiza posiłku (tekst lub obraz).
    """
    try:
        # Używamy analyze_meal_text, bo tak nazwaliśmy funkcję w legacy_analyzer.py
        analysis_result = await ai_analyzer.analyze_meal_text(
            text=request.text
        )
        
        if not analysis_result:
            raise HTTPException(status_code=400, detail="AI nie mogło przeanalizować produktu.")
        
        # Mapowanie wyniku na format AnalysisResponse (jeśli AI zwróciło inną strukturę)
        return {
            "aggregated_meal": analysis_result.get("aggregated_meal", {}),
            "deconstruction_details": analysis_result.get("deconstruction_details", [])
        }

    except Exception as e:
        print(f"Błąd analizy posiłku: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd serwera: {e}")


# --- ENDPOINTY DLA AI CHEFA ---
@router.get("/suggest-diet-plan", response_model=list[schemas.DietPlanSuggestion])
async def get_diet_plan_suggestion(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generuje plan dietetyczny."""
    today = date.today()
    if current_user.last_request_date == today and current_user.diet_plan_requests >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limit planów na dziś wyczerpany."
        )

    if current_user.last_request_date != today:
        current_user.diet_plan_requests = 0
        current_user.last_request_date = today

    macros = { "calorie_goal": current_user.calorie_goal, "protein_goal": current_user.protein_goal, "fat_goal": current_user.fat_goal, "carb_goal": current_user.carb_goal }
    
    # Wywołanie AI
    plan = await ai_analyzer.suggest_diet_plan(current_user.preferences, macros)
    
    if not plan:
        # Fallback (gdyby AI zawiodło)
        return []
    
    current_user.diet_plan_requests += 1
    plan_json_string = json.dumps(plan, default=str)
    
    # Aktualizacja użytkownika
    current_user.last_diet_plan = plan_json_string
    db.add(current_user)
    db.commit()
    
    return plan


# --- ENDPOINTY DLA ANALIZY TYGODNIOWEJ (NAPRAWIONE OBLICZENIA) ---

@router.post("/generate", response_model=schemas.WeeklyAnalysisResponse)
async def generate_weekly_analysis_endpoint(
    request: schemas.AnalysisGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Generuje analizę (Tekst + Statystyki)."""
    
    # Sprawdzenie limitu czasu (raz na 24h)
    if current_user.last_analysis_generated_at and (datetime.now() - current_user.last_analysis_generated_at < timedelta(hours=24)):
         # (Możesz odkomentować to sprawdzenie na produkcji, na devie lepiej testować bez blokady)
         pass

    start_date, end_date = request.start_date, request.end_date
    
    # Pobranie danych z bazy
    meals = crud.get_meals_by_date_range(db, current_user.id, start_date, end_date)
    workouts = crud.get_workouts_by_date_range(db, current_user.id, start_date, end_date)
    weight_history = crud.get_weight_history_by_date_range(db, current_user.id, start_date, end_date)
    
    # Generowanie podsumowania tekstowego przez AI
    ai_coach_summary = await ai_analyzer.generate_weekly_analysis(
        {"meals": meals, "workouts": workouts, "weight_history": weight_history}, 
        user=current_user, start_date=start_date, end_date=end_date
    )

    # --- TU BYŁ BŁĄD: BRAKOWAŁO OBLICZEŃ STATYSTYCZNYCH ---
    
    # 1. Oblicz średnie makro
    total_cals = sum(e.calories for m in meals for e in m.entries)
    total_protein = sum(e.protein for m in meals for e in m.entries)
    total_fat = sum(e.fat for m in meals for e in m.entries)
    total_carbs = sum(e.carbs for m in meals for e in m.entries)
    
    days_count = (end_date - start_date).days + 1
    
    avg_macros = {
        "calories": round(total_cals / days_count) if days_count else 0,
        "protein": round(total_protein / days_count, 1) if days_count else 0,
        "fat": round(total_fat / days_count, 1) if days_count else 0,
        "carbs": round(total_carbs / days_count, 1) if days_count else 0
    }

    # 2. Statystyki treningowe
    total_burned = sum(w.calories_burned for w in workouts)
    
    # 3. Wykres wagi
    weight_chart = {
        "labels": [w.date.isoformat() for w in weight_history],
        "values": [w.weight for w in weight_history]
    }

    # 4. Budowa pełnej odpowiedzi (zgodnej ze schematem WeeklyAnalysisResponse)
    analysis_data = schemas.WeeklyAnalysisResponse(
        ai_coach_summary=ai_coach_summary,
        avg_macros=avg_macros,
        total_workouts=len(workouts),
        total_calories_burned=total_burned,
        weight_chart_data=weight_chart,
        analysis_start_date=start_date,
        analysis_end_date=end_date
    )
    
    # Zapis do bazy
    current_user.last_weekly_analysis = analysis_data.model_dump_json()
    current_user.last_analysis_generated_at = datetime.now()
    db.add(current_user)
    db.commit()
    
    return analysis_data

@router.get("/latest", response_model=schemas.WeeklyAnalysisResponse)
async def get_latest_weekly_analysis_endpoint(
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.last_weekly_analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brak analizy.")
    
    try:
        return schemas.WeeklyAnalysisResponse.model_validate_json(current_user.last_weekly_analysis)
    except Exception:
        raise HTTPException(status_code=500, detail="Błąd odczytu analizy.")