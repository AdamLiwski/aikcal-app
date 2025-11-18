from datetime import datetime, timedelta
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sql_models import User
from app.core.security import get_password_hash
from app.core.config import settings
# UWAGA: Zakładam, że przeniesiemy email_utils.py później.
# Jeśli jeszcze go nie ma, zakomentuj import i linię z send_reset_password_email
# from app.services.email_service import send_reset_password_email 

router = APIRouter()

@router.post("/request-password-reset")
def request_password_reset(
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db),
) -> Any:
    """
    Generuje token resetowania hasła i (opcjonalnie) wysyła e-mail.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Dla bezpieczeństwa nie mówimy, że użytkownika nie ma, tylko zwracamy sukces
        return {"msg": "Jeśli e-mail istnieje, wysłano instrukcję resetowania hasła."}
    
    # Generujemy token (UUID)
    token = str(uuid.uuid4())
    user.password_reset_token = token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
    db.add(user)
    db.commit()

    # TU POWINNO BYĆ WYSYŁANIE MAILA
    # send_reset_password_email(email_to=user.email, token=token)
    print(f"🔑 DEV MODE - Token resetowania dla {email}: {token}") 

    return {"msg": "Password recovery email sent"}

@router.post("/reset-password")
def reset_password(
    token: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(get_db),
) -> Any:
    """
    Zmienia hasło na podstawie ważnego tokena.
    """
    user = db.query(User).filter(
        User.password_reset_token == token,
        User.password_reset_expires > datetime.utcnow()
    ).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.hashed_password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.add(user)
    db.commit()
    
    return {"msg": "Password updated successfully"}