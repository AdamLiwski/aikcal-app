from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.orm.attributes import flag_modified # Upewnij się, że masz ten import
from datetime import date, datetime, timedelta
import json

# --- ZAKTUALIZOWANE IMPORTY DLA CLEAN ARCHITECTURE ---

# Modele SQL
from app.models.sql_models import (
    User, Meal, MealEntry, WaterEntry, WeightEntry, Workout,
    Dish, DishIngredient, Product, Friendship, UserChallenge, Conversation, ChatMessage
)
# Schematy Pydantic
from app.schemas.all_schemas import (
    UserCreate, UserUpdate, MealCreate, MealEntryCreate, WaterEntryCreate,
    WeightEntryCreate, WorkoutCreate, ProductCreate, DishCreate, FriendshipStatus,
    ChallengeStatus # Przeniesienie Enumów do schematów/bazowej lokalizacji
)
# Bezpieczeństwo
from app.core.security import get_password_hash
# Enums, jeśli nie są częścią schematów (zakładam, że powinny być globalne lub w schemas)
# ZAKŁADAM, ŻE FriendshipStatus, ChallengeStatus SĄ DOSTĘPNE W all_schemas
# Usuwam pierwotne importy schemas i models
# from . import models, schemas
# from .security import get_password_hash
# from .enums import ChallengeStatus, FriendshipStatus, SubscriptionStatus

# --- User Operations ---

def get_user_by_email(db: Session, email: str):
    """Pobiera użytkownika po jego adresie email."""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    """Pobiera użytkownika po jego unikalnym ID."""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, user: UserCreate):
    """Tworzy nowego użytkownika, hashuje jego hasło i ustawia dane początkowe."""
    hashed_password = get_password_hash(user.password) if user.password else None
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    # Tworzy początkowy wpis wagi dla nowego użytkownika
    weight_entry = WeightEntry(weight=70.0, owner_id=db_user.id, date=date.today())
    db.add(weight_entry)
    # Tworzy domyślną, początkową konwersację dla użytkownika
    create_conversation(db, user_id=db_user.id, title="Pierwszy czat")
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: User, user_update: UserUpdate):
    """Aktualizuje informacje profilowe użytkownika, w tym jego dzienny wpis wagi."""
    update_data = user_update.model_dump(exclude_unset=True)
    if 'weight' in update_data and update_data['weight'] is not None:
        # Sprawdza, czy wpis wagi na dzisiaj już istnieje
        today_weight_entry = db.query(WeightEntry).filter(
            WeightEntry.owner_id == db_user.id, WeightEntry.date == date.today()
        ).first()
        if today_weight_entry:
            # Aktualizuje istniejący wpis
            today_weight_entry.weight = update_data['weight']
        else:
            # Tworzy nowy wpis na dzisiaj
            weight_entry = WeightEntry(weight=update_data['weight'], owner_id=db_user.id, date=date.today())
            db.add(weight_entry)
        del update_data['weight'] # Usuwa wagę ze słownika, aby uniknąć ustawiania jej bezpośrednio w modelu User
    # Aktualizuje inne atrybuty użytkownika
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    """Usuwa użytkownika z bazy danych."""
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

# --- NOWE, RELACYJNE OPERACJE NA ŻYWNOŚCI ---

def get_product_by_name(db: Session, name: str):
    """Wyszukuje produkt podstawowy po jego unikalnej nazwie (ignoruje wielkość liter)."""
    return db.query(Product).filter(func.lower(Product.name) == func.lower(name)).first()

def create_product(db: Session, product: ProductCreate) -> Product:
    """Tworzy nowy produkt podstawowy w bazie."""
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def get_dish_by_name(db: Session, name: str):
    """Wyszukuje danie po jego unikalnej nazwie (ignoruje wielkość liter)."""
    return db.query(Dish).filter(func.lower(Dish.name) == func.lower(name)).first()

def create_dish_with_ingredients(db: Session, dish: DishCreate) -> Dish:
    """Tworzy nowe danie i jego powiązania ze składnikami."""
    db_dish = Dish(name=dish.name, category=dish.category, aliases=dish.aliases)
    db.add(db_dish)
    db.commit()
    db.refresh(db_dish)

    for ing in dish.ingredients:
        db_product = get_product_by_name(db, name=ing.product_name)
        # Jeśli produkt składnika nie istnieje, utwórz dla niego symbol zastępczy
        if not db_product:
            placeholder_product = ProductCreate(
                name=ing.product_name,
                nutrients={"calories": 0, "protein": 0, "fat": 0, "carbs": 0},
                state="SOLID" # Zakładając, że ProductState jest zaimportowany lub używamy surowego ciągu/enum
            )
            db_product = create_product(db, placeholder_product)
        # Utwórz połączenie między daniem a składnikiem
        db_dish_ingredient = DishIngredient(
            dish_id=db_dish.id, product_id=db_product.id, weight_g=ing.weight_g
        )
        db.add(db_dish_ingredient)
    db.commit()
    db.refresh(db_dish)
    return db_dish

# --- NOWE OPERACJE DLA WIELOWĄTKOWEGO CZATU ---

def get_user_conversations(db: Session, user_id: int):
    """Pobiera wszystkie konwersacje użytkownika, najnowsze i przypięte na górze."""
    return db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.is_pinned.desc(), Conversation.created_at.desc()).all()

def get_conversation_by_id(db: Session, conversation_id: int, user_id: int):
    """Pobiera jedną konwersację, sprawdzając, czy należy do użytkownika."""
    return db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()

def create_conversation(db: Session, user_id: int, title: str = "Nowy czat"):
    """Tworzy nową, pustą konwersację dla użytkownika."""
    db_conversation = Conversation(user_id=user_id, title=title)
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

def add_message_to_conversation(db: Session, conversation_id: int, role: str, content: str):
    """Dodaje nową wiadomość do istniejącej konwersacji i aktualizuje jej znacznik czasu."""
    db_message = ChatMessage(conversation_id=conversation_id, role=role, content=content)
    db.add(db_message)
    conversation = db.query(Conversation).filter_by(id=conversation_id).first()
    if conversation:
        # Aktualizuje 'created_at', aby działało jako znacznik czasu 'updated_at'
        conversation.created_at = datetime.utcnow()
    db.commit()
    db.refresh(db_message)
    return db_message

# --- Meal Operations ---

def create_user_meal(db: Session, meal: MealCreate, user_id: int):
    """Tworzy wpis posiłku dla użytkownika."""
    db_meal = Meal(**meal.model_dump(), owner_id=user_id)
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    return db_meal

def add_entry_to_meal(db: Session, entry: MealEntryCreate, meal_id: int):
    """Dodaje wpis żywnościowy do określonego posiłku."""
    db_entry = MealEntry(
        product_name=entry.product_name,
        calories=entry.calories, protein=entry.protein, fat=entry.fat, carbs=entry.carbs,
        original_amount=entry.amount, original_unit=entry.unit,
        standardized_grams=entry.amount, # Zakładając, że ilość jest już standaryzowana
        meal_id=meal_id,
        deconstruction_details=entry.deconstruction_details,
        display_quantity_text=entry.display_quantity_text,
        is_default_quantity=entry.is_default_quantity
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

# --- ZMIENIONA FUNKCJA ---
def update_meal_entry(db: Session, entry_id: int, entry_data: MealEntryCreate):
    """Aktualizuje wpis w posiłku, w tym jego składniki (deconstruction_details)."""
    # Znajdujemy wpis w bazie danych. Zakładamy, że autoryzacja (sprawdzenie user_id)
    # odbywa się na poziomie endpointu API, a nie tutaj.
    db_entry = db.query(MealEntry).filter(MealEntry.id == entry_id).first()
    if not db_entry:
        return None

    # Pobieramy dane do aktualizacji z modelu Pydantic
    update_data = entry_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        # --- KLUCZOWA ZMIANA ---
        # Sprawdzamy, czy aktualizujemy pole ze składnikami
        if key == "deconstruction_details":
            db_entry.deconstruction_details = value
            # Mówimy bazie, że to pole JSON zostało zmodyfikowane
            flag_modified(db_entry, "deconstruction_details")
        else:
            # Dla wszystkich innych pól używamy standardowego setattr
            setattr(db_entry, key, value)

    db.commit()
    db.refresh(db_entry)
    return db_entry

def get_meals_by_date(db: Session, user_id: int, target_date: date):
    """Pobiera posiłki użytkownika z określonej daty."""
    return db.query(Meal).filter(
        Meal.owner_id == user_id,
        func.date(Meal.date) == target_date
    ).all()

def get_meals_by_date_range(db: Session, user_id: int, start_date: date, end_date: date):
    """Pobiera posiłki użytkownika z zadanego okresu."""
    query = db.query(Meal).filter(Meal.owner_id == user_id)
    query = query.filter(Meal.date.between(start_date, end_date))
    return query.order_by(Meal.date).all()

def delete_meal(db: Session, meal_id: int, user_id: int):
    """Usuwa posiłek."""
    db_meal = db.query(Meal).filter(Meal.id == meal_id, Meal.owner_id == user_id).first()
    if db_meal:
        db.delete(db_meal)
        db.commit()
        return True
    return False

def delete_meal_entry(db: Session, entry_id: int, user_id: int):
    """Usuwa wpis z posiłku."""
    db_entry = db.query(MealEntry).join(Meal).filter(
        MealEntry.id == entry_id, Meal.owner_id == user_id
    ).first()
    if db_entry:
        db.delete(db_entry)
        db.commit()
        return True
    return False

# --- Water and Workout Operations ---

def add_water_entry(db: Session, water_entry: WaterEntryCreate, user_id: int):
    """Dodaje wpis o spożyciu wody."""
    db_entry = WaterEntry(**water_entry.model_dump(), owner_id=user_id)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

def get_water_entries_by_date(db: Session, user_id: int, target_date: date):
    """Pobiera wpisy o wodzie z określonej daty."""
    return db.query(WaterEntry).filter(
        WaterEntry.owner_id == user_id,
        func.date(WaterEntry.date) == target_date
    ).all()

def delete_water_entry(db: Session, water_entry_id: int, user_id: int):
    """Usuwa wpis o wodzie."""
    db_entry = db.query(WaterEntry).filter(WaterEntry.id == water_entry_id, WaterEntry.owner_id == user_id).first()
    if db_entry:
        db.delete(db_entry)
        db.commit()
        return True
    return False

def create_workout(db: Session, workout: WorkoutCreate, user_id: int):
    """Tworzy wpis o treningu."""
    db_workout = Workout(**workout.model_dump(), owner_id=user_id)
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout

def get_workouts_by_date(db: Session, user_id: int, target_date: date):
    """Pobiera treningi z określonej daty."""
    return db.query(Workout).filter(
        Workout.owner_id == user_id,
        func.date(Workout.date) == target_date
    ).all()

def get_workouts_by_date_range(db: Session, user_id: int, start_date: date, end_date: date):
    """Pobiera treningi z zadanego okresu."""
    query = db.query(Workout).filter(Workout.owner_id == user_id)
    query = query.filter(Workout.date.between(start_date, end_date))
    return query.all()

def delete_workout(db: Session, workout_id: int, user_id: int):
    """Usuwa trening."""
    db_workout = db.query(Workout).filter(Workout.id == workout_id, Workout.owner_id == user_id).first()
    if db_workout:
        db.delete(db_workout)
        db.commit()
        return True
    return False

def get_weight_history_by_date_range(db: Session, user_id: int, start_date: date, end_date: date):
    """Pobiera historię wagi z zadanego okresu."""
    return db.query(WeightEntry).filter(
        WeightEntry.owner_id == user_id,
        WeightEntry.date.between(start_date, end_date)
    ).order_by(WeightEntry.date).all()

# --- Social Operations ---

def search_users_by_email(db: Session, email_query: str, current_user_id: int, limit: int = 10):
    """Wyszukuje użytkowników po emailu do celów społecznościowych."""
    return db.query(User).filter(
        User.email.ilike(f"%{email_query}%"),
        User.id != current_user_id,
        User.is_social_profile_active == True
    ).limit(limit).all()

def get_friendship(db: Session, user_id: int, friend_id: int):
    """Pobiera relację przyjaźni między dwoma użytkownikami."""
    return db.query(Friendship).filter(
        or_((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id),
            (Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
    ).first()

def send_friend_request(db: Session, user_id: int, friend_id: int):
    """Wysyła zaproszenie do znajomych."""
    # FriendshipStatus musi być zaimportowany, zakładam, że jest w schemas
    db_friendship = Friendship(user_id=user_id, friend_id=friend_id, status=FriendshipStatus.PENDING)
    db.add(db_friendship)
    db.commit()
    db.refresh(db_friendship)
    return db_friendship

def get_friendship_by_id(db: Session, friendship_id: int):
    """Pobiera relację przyjaźni po jej ID."""
    return db.query(Friendship).filter(Friendship.id == friendship_id).first()

def get_friend_requests(db: Session, user_id: int):
    """Pobiera zaproszenia do znajomych oczekujące na akceptację."""
    # FriendshipStatus musi być zaimportowany, zakładam, że jest w schemas
    return db.query(Friendship).filter(
        Friendship.friend_id == user_id,
        Friendship.status == FriendshipStatus.PENDING
    ).all()

def update_friendship_status(db: Session, db_friendship: Friendship, status: FriendshipStatus):
    """Aktualizuje status przyjaźni (np. akceptuje zaproszenie)."""
    db_friendship.status = status
    db.commit()
    db.refresh(db_friendship)
    return db_friendship

def get_friends_list(db: Session, user_id: int):
    """Pobiera listę znajomych użytkownika."""
    # FriendshipStatus musi być zaimportowany, zakładam, że jest w schemas
    accepted_friendships = db.query(Friendship).filter(
        or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
        Friendship.status == FriendshipStatus.ACCEPTED
    ).all()
    friend_ids = {f.user_id if f.user_id != user_id else f.friend_id for f in accepted_friendships}
    if not friend_ids: return []
    return db.query(User).filter(User.id.in_(friend_ids)).all()

def delete_friendship(db: Session, db_friendship: Friendship):
    """Usuwa relację przyjaźni."""
    db.delete(db_friendship)
    db.commit()
    return True

# --- Challenge Operations ---

def get_user_challenge(db: Session, user_id: int, challenge_id: int):
    """Pobiera wyzwanie podjęte przez użytkownika."""
    return db.query(UserChallenge).filter_by(user_id=user_id, challenge_id=challenge_id).first()

def create_user_challenge(db: Session, user_id: int, challenge_id: int, duration_days: int):
    """Tworzy wpis o podjęciu wyzwania przez użytkownika."""
    start_date = date.today()
    end_date = start_date + timedelta(days=duration_days)
    # ChallengeStatus musi być zaimportowany, zakładam, że jest w schemas
    db_user_challenge = UserChallenge(
        user_id=user_id,
        challenge_id=challenge_id,
        start_date=start_date,
        end_date=end_date,
        status=ChallengeStatus.ACTIVE
    )
    db.add(db_user_challenge)
    db.commit()
    db.refresh(db_user_challenge)
    return db_user_challenge

def get_user_challenges(db: Session, user_id: int):
    """Pobiera wszystkie wyzwania użytkownika."""
    return db.query(UserChallenge).filter_by(user_id=user_id).order_by(UserChallenge.start_date.desc()).all()

def get_recently_completed_challenges_for_user(db: Session, user_id: int):
    """Pobiera niedawno ukończone wyzwania użytkownika."""
    one_week_ago = date.today() - timedelta(days=7)
    # ChallengeStatus musi być zaimportowany, zakładam, że jest w schemas
    return db.query(UserChallenge).filter(
        UserChallenge.user_id == user_id,
        UserChallenge.status == ChallengeStatus.COMPLETED,
        UserChallenge.end_date >= one_week_ago
    ).all()

def get_active_challenges_to_verify(db: Session):
    """Pobiera aktywne wyzwania, których termin minął, do weryfikacji."""
    # ChallengeStatus musi być zaimportowany, zakładam, że jest w schemas
    return db.query(UserChallenge).filter(
        UserChallenge.status == ChallengeStatus.ACTIVE,
        UserChallenge.end_date < date.today()
    ).all()

def update_user_challenge_status(db: Session, user_challenge_id: int, status: ChallengeStatus):
    """Aktualizuje status wyzwania użytkownika."""
    db_challenge = db.query(UserChallenge).filter_by(id=user_challenge_id).first()
    if db_challenge:
        db_challenge.status = status
        db.commit()
        db.refresh(db_challenge)
        return db_challenge
    return None

# --- Password Reset Token Operations ---

def create_password_reset_token(db: Session, user_id: int, token: str):
    """Tworzy token resetu hasła i zapisuje go w bazie."""
    user = get_user_by_id(db, user_id)
    if user:
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()

def get_user_by_password_reset_token(db: Session, token: str):
    """Znajduje użytkownika na podstawie tokenu resetującego hasło."""
    return db.query(User).filter(
        User.password_reset_token == token,
        User.password_reset_expires > datetime.utcnow()
    ).first()