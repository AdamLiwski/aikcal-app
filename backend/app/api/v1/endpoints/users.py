from datetime import timedelta, date
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.core.config import settings
# --- ZMIANA: Dodano WeightEntry do importów ---
from app.models.sql_models import User, WeightEntry
from app.schemas.all_schemas import UserCreate, UserUpdate, UserResponse, Token 
from app.schemas.all_schemas import GoalSuggestionRequest, MacroSuggestion
from app.api import deps

router = APIRouter()

# --- LOGOWANIE ---
@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = deps.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Używamy czasu wygasania z ustawień
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_name": user.name}

# --- REJESTRACJA ---
@router.post("/register", response_model=UserResponse)
def register_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    hashed_pw = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_pw,
        name="Użytkownik" # Domyślna nazwa
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- PROFIL UŻYTKOWNIKA ---
@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Aktualizuje profil i wymusza odświeżenie danych (wagi).
    """
    user_data = user_in.dict(exclude_unset=True)

    # 1. Obsługa Wagi (Tabela WeightEntry)
    if "weight" in user_data:
        new_weight = user_data.pop("weight")
        if new_weight is not None:
            print(f"⚖️ Zapisywanie nowej wagi: {new_weight}")
            weight_entry = WeightEntry(
                weight=new_weight,
                date=date.today(),
                owner_id=current_user.id
            )
            db.add(weight_entry)

    # 2. Obsługa reszty pól (Tabela User)
    for field, value in user_data.items():
        if hasattr(current_user, field):
            print(f"✏️ Aktualizacja {field} -> {value}")
            setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    
    # --- KLUCZOWA ZMIANA: ODŚWIEŻAMY WSZYSTKO ---
    # expire_all() zmusza SQLAlchemy do ponownego pobrania danych z bazy przy następnym użyciu.
    # To gwarantuje, że pole 'weight' (które jest @property) przeliczy się na nowo!
    db.expire_all()
    
    # Pobieramy użytkownika na świeżo, żeby mieć pewność, że relacja weights jest załadowana
    updated_user = db.query(User).filter(User.id == current_user.id).first()
    
    return updated_user

@router.post("/suggest-goals", response_model=MacroSuggestion)
def suggest_goals(
    request: GoalSuggestionRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Sugeruje cele kaloryczne i makro na podstawie danych użytkownika (AI).
    """
    # --- FIX: IMPORT LOKALNY (Przecina pętlę importów) ---
    from app.services.legacy_analyzer import analyze_meal_text 
    
    # Tworzymy prompt dla AI
    prompt = f"""
    Jesteś dietetykiem. Oblicz zapotrzebowanie dla:
    Płeć: {request.gender}
    Wiek: {date.today().year - request.date_of_birth.year} lat
    Wzrost: {request.height} cm
    Waga: {request.weight} kg
    Aktywność: {request.activity_level}
    Cel wagi: {request.target_weight} kg
    Tempo zmiany: {request.weekly_goal_kg} kg/tydzień
    Dieta: {request.diet_style}

    Zwróć TYLKO JSON:
    {{
        "calorie_goal": 0,
        "protein_goal": 0,
        "fat_goal": 0,
        "carb_goal": 0
    }}
    """
    
    try:
        # Wywołujemy funkcję zaimportowaną lokalnie
        result = analyze_meal_text(prompt) 
        
        if result:
            return MacroSuggestion(
                calorie_goal=result.get("calorie_goal", result.get("calories", 2000)),
                protein_goal=result.get("protein_goal", result.get("protein", 100)),
                fat_goal=result.get("fat_goal", result.get("fat", 70)),
                carb_goal=result.get("carb_goal", result.get("carbs", 250))
            )
    except Exception as e:
        print(f"Błąd AI Goals: {e}")
    
    return MacroSuggestion(
        calorie_goal=2000, protein_goal=100, fat_goal=70, carb_goal=250
    )