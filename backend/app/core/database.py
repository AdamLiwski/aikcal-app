from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Używamy SQLite lokalnie (plik powstanie w folderze backend/app w kontenerze)
SQLALCHEMY_DATABASE_URL = "sqlite:////app/app/sql_app.db"

# Tworzenie silnika (engine)
# connect_args={"check_same_thread": False} jest wymagane tylko dla SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Fabryka sesji - to z niej będziesz korzystać w endpointach
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Klasa bazowa dla Twoich modeli (User, Meal, itp.)
Base = declarative_base()

# Funkcja dependency do wstrzykiwania sesji w FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()