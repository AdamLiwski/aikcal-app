from datetime import timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.core.config import settings
from app.models.sql_models import User
# UWAGA: Tutaj zakładamy, że zaraz stworzymy ten plik ze schematami
from app.schemas.all_schemas import UserCreate, UserUpdate, UserResponse, Token 
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
    
    access_token_expires = timedelta(minutes=30) # Można przenieść do settings
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

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
    Update own user.
    """
    # Aktualizacja pól użytkownika
    user_data = user_in.dict(exclude_unset=True)
    for field, value in user_data.items():
        setattr(current_user, field, value)

    # Prosta logika AI dla celów (jeśli zmieniono wagę/cel)
    if user_in.target_weight or user_in.weekly_goal_kg:
        # Tu kiedyś wstawimy logikę przeliczania kalorii
        pass

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user