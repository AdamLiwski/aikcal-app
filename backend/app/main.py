from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.core.config import settings
# IMPORTUJEMY WSZYSTKIE ROUTERY
from app.api.v1.endpoints import (
    users, auth_actions, auth_google, 
    summary, meals, workouts, 
    analysis, chat, social, challenges
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://aikcal.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REJESTRACJA WSZYSTKICH ROUTERÓW ---
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(auth_actions.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth_google.router, prefix="/api/auth", tags=["google"])
app.include_router(summary.router, prefix="/api/summary", tags=["summary"])
app.include_router(meals.router, prefix="/api/meals", tags=["meals"])
app.include_router(workouts.router, prefix="/api/workouts", tags=["workouts"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(social.router, prefix="/api/social", tags=["social"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["challenges"])

# Obsługa Frontendu
FRONTEND_DIR = "/app/frontend"

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    
    @app.get("/")
    async def read_root():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
    
    @app.get("/{filename}.html")
    async def read_html(filename: str):
        file_path = os.path.join(FRONTEND_DIR, f"{filename}.html")
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return {"error": "File not found"}
        
    @app.get("/{filename}.css")
    async def read_css(filename: str):
         return FileResponse(os.path.join(FRONTEND_DIR, f"{filename}.css"))

    @app.get("/{filename}.js")
    async def read_js(filename: str):
         return FileResponse(os.path.join(FRONTEND_DIR, f"{filename}.js"))

else:
    print(f"⚠️ Ostrzeżenie: Nie znaleziono folderu frontend w {FRONTEND_DIR}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "db": "seeded", "modules": "all loaded"}