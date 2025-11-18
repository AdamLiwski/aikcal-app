from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.core.config import settings
from app.api.v1.endpoints import users, auth_actions, auth_google



app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 1. Konfiguracja CORS (Bezpieczeństwo przeglądarki)
# Pozwalamy na zapytania z localhost (dla developmentu)
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Tu wkrótce podłączymy Routery API (np. /api/v1/meals)
# app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(auth_actions.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth_google.router, prefix="/api/auth", tags=["google"])

# 3. Obsługa Frontendu (Pliki statyczne)
# Ścieżka do folderu frontend wewnątrz kontenera
FRONTEND_DIR = "/app/frontend"

if os.path.isdir(FRONTEND_DIR):
    # Serwowanie plików CSS, JS, obrazków
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    
    # Serwowanie index.html na stronie głównej
    @app.get("/")
    async def read_root():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
    
    # Obsługa innych plików HTML (np. regulamin.html)
    @app.get("/{filename}.html")
    async def read_html(filename: str):
        file_path = os.path.join(FRONTEND_DIR, f"{filename}.html")
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return {"error": "File not found"}
        
    # Fix dla plików w głównym katalogu (style.css, app.js)
    # Jeśli index.html szuka "style.css" bez prefiksu /static
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
    return {"status": "ok", "db": "seeded"}