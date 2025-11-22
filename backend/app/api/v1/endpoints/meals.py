from typing import List, Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# --- IMPORTY SYSTEMOWE I ZALEŻNOŚCI ---
from app.core.database import get_db
from app.api import deps
from app.models import sql_models as models
from app.schemas import all_schemas as schemas
from app.crud import crud_base as crud

# --- AI ANALYZER (Gotowy do użycia, jeśli dodasz endpoint analizy) ---
# from app.services import legacy_analyzer

router = APIRouter(
    tags=["Dziennik (Posiłki i Woda)"],
    responses={404: {"description": "Not found"}},
)

# --- ENDPOINTY DLA POSIŁKÓW (MEALS) ---

@router.post("/meals", response_model=schemas.Meal)
def create_meal(
    meal: schemas.MealCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Tworzy nowy kontener na posiłek (np. Śniadanie, Obiad) dla danego dnia.
    """
    return crud.create_user_meal(db=db, meal=meal, user_id=current_user.id)

@router.post("/meals/{meal_id}/entries", response_model=schemas.MealEntry)
def add_meal_entry(
    meal_id: int,
    entry: schemas.MealEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Dodaje pojedynczy wpis (produkt) do istniejącego posiłku.
    Sprawdza, czy posiłek należy do zalogowanego użytkownika.
    """
    # Bezpośrednie sprawdzenie własności posiłku przed dodaniem wpisu
    # Można to również przenieść do CRUD, ale tutaj daje jasny błąd 404 dla API
    db_meal = db.query(models.Meal).filter(
        models.Meal.id == meal_id,
        models.Meal.owner_id == current_user.id
    ).first()

    if not db_meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Posiłek nie został znaleziony lub nie należy do Ciebie."
        )
    
    return crud.add_entry_to_meal(db=db, entry=entry, meal_id=meal_id)

@router.get("/meals", response_model=List[schemas.Meal])
def read_meals(
    date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Pobiera wszystkie posiłki użytkownika z określonego dnia.
    """
    return crud.get_meals_by_date(db=db, user_id=current_user.id, target_date=date)

@router.delete("/meals/{meal_id}", status_code=status.HTTP_200_OK)
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Usuwa cały posiłek (np. całe śniadanie) wraz ze wszystkimi jego wpisami.
    """
    success = crud.delete_meal(db=db, meal_id=meal_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Posiłek nie został znaleziony."
        )
    return None

@router.put("/meals/entries/{entry_id}", response_model=schemas.MealEntry)
def update_meal_entry(
    entry_id: int,
    entry_update: schemas.MealEntryCreate, # Używamy schematu Create jako Update (chyba że masz dedykowany Update)
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Aktualizuje istniejący wpis w posiłku (np. zmienia gramaturę).
    """
    # Logika w CRUD powinna sprawdzać własność poprzez join do tabeli Meal
    updated_entry = crud.update_meal_entry(db=db, entry_id=entry_id, entry_data=entry_update)
    
    if not updated_entry:
        # Jeśli CRUD zwrócił None, to albo wpis nie istnieje, albo user nie ma praw
        # (zależy od implementacji CRUD, zakładamy bezpieczny default 404)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wpis posiłku nie został znaleziony lub nie masz do niego uprawnień."
        )
    return updated_entry

@router.delete("/meals/entries/{entry_id}", status_code=status.HTTP_200_OK)
def delete_meal_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Usuwa pojedynczy wpis (produkt) z posiłku.
    """
    success = crud.delete_meal_entry(db=db, entry_id=entry_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wpis posiłku nie został znaleziony."
        )
    return None

# --- ENDPOINTY DLA WODY (WATER) ---

@router.post("/water", response_model=schemas.WaterEntry)
def add_water(
    water_entry: schemas.WaterEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Dodaje wpis o spożyciu wody.
    """
    return crud.add_water_entry(db=db, water_entry=water_entry, user_id=current_user.id)

@router.delete("/water/{entry_id}", status_code=status.HTTP_200_OK)
def delete_water(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    Usuwa wpis o spożyciu wody.
    """
    success = crud.delete_water_entry(db=db, water_entry_id=entry_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wpis wody nie został znaleziony."
        )
    return None