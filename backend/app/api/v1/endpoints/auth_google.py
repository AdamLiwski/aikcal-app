from datetime import timedelta
from typing import Any
import requests

from fastapi import APIRouter, Depends, HTTPException
# IMPORT ZMIANY: Potrzebujemy RedirectResponse
from fastapi.responses import RedirectResponse 
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.models.sql_models import User

router = APIRouter()

@router.get("/callback/google")
def google_auth_callback(
    code: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Callback z Google OAuth. Wymienia 'code' na token i przekierowuje na Frontend.
    """
    # 1. Wymiana kodu na token Google
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        # Pamiętaj: to musi być ten sam adres co w konsoli Google!
        "redirect_uri": "http://localhost:8000/api/auth/callback/google"
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Google code")
    
    google_token = response.json().get("access_token")
    
    # 2. Pobranie danych użytkownika
    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    user_info_resp = requests.get(user_info_url, headers={"Authorization": f"Bearer {google_token}"})
    if user_info_resp.status_code != 200:
         raise HTTPException(status_code=400, detail="Failed to get user info")
         
    user_data = user_info_resp.json()
    email = user_data.get("email")
    
    if not email:
         raise HTTPException(status_code=400, detail="Google account has no email")

    # 3. Znajdź lub stwórz użytkownika
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=user_data.get("name", "Użytkownik Google"),
            is_verified=True,
            is_social_profile_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4. Wygeneruj Token
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    
    # --- ZMIANA: Zamiast zwracać JSON, robimy przekierowanie na Dashboard ---
    # Frontend (app.js) przechwyci parametr ?token=... i zaloguje użytkownika
    return RedirectResponse(url=f"http://localhost:8000?token={access_token}")