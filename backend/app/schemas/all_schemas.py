from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import date, time as time_class, datetime

# --- ZAKTUALIZOWANE IMPORTY ENUMÓW ---
from app.models.enums import (
    MealCategory, 
    Gender, 
    ActivityLevel, 
    DietStyle, 
    FriendshipStatus, 
    ChallengeStatus, 
    SubscriptionStatus, 
    ProductState
)

# --- SCHEMATY PODSTAWOWE ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user_name: Optional[str] = None # Dodano dla wygody

class TokenData(BaseModel):
    email: Optional[str] = None

# --- NOWE, RELACYJNE SCHEMATY DLA ŻYWNOŚCI ---

class ProductBase(BaseModel):
    name: str
    aliases: Optional[List[str]] = []
    nutrients: Dict[str, float] 
    state: ProductState

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    class Config:
        from_attributes = True

class DishIngredientBase(BaseModel):
    product_name: str
    weight_g: float

class DishIngredientCreate(DishIngredientBase):
    pass

class DishIngredient(DishIngredientBase):
    product: Product 
    class Config:
        from_attributes = True

class DishBase(BaseModel):
    name: str
    category: Optional[str] = None
    aliases: Optional[List[str]] = []

class DishCreate(DishBase):
    ingredients: List[DishIngredientCreate]

class Dish(DishBase):
    id: int
    ingredients: List[DishIngredient] = []
    class Config:
        from_attributes = True

# --- NOWE SCHEMATY DLA WIELOWĄTKOWEGO CZATU ---

class ChatMessageBase(BaseModel):
    content: str

class ChatMessageCreate(ChatMessageBase):
    role: str

class ChatMessage(ChatMessageBase):
    id: int
    role: str
    created_at: datetime
    class Config:
        from_attributes = True

class ConversationInfo(BaseModel):
    id: int
    title: str
    created_at: datetime
    is_pinned: bool
    class Config:
        from_attributes = True

class Conversation(ConversationInfo):
    messages: List[ChatMessage] = []

# --- ZAKTUALIZOWANE SCHEMATY UŻYTKOWNIKA ---

# --- DODANO BRAKUJĄCĄ KLASĘ USER BASE ---
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    
    # Profilowe
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    height: Optional[float] = None
    # Waga nie jest tu potrzebna, bo jest @property
    
    # Cele
    target_weight: Optional[float] = None
    weekly_goal_kg: Optional[float] = 0.0
    activity_level: Optional[ActivityLevel] = ActivityLevel.SEDENTARY
    diet_style: Optional[DietStyle] = DietStyle.BALANCED
    
    # Makro
    calorie_goal: Optional[int] = 2000
    protein_goal: Optional[int] = 100
    fat_goal: Optional[int] = 70
    carb_goal: Optional[int] = 250
    water_goal: Optional[int] = 2500
    
    add_workout_calories_to_goal: Optional[bool] = False
    is_social_profile_active: Optional[bool] = True
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: EmailStr
    password: Optional[str] = None 

class UserPreferences(BaseModel):
    proteins: List[str]
    carbs: List[str]
    fats: List[str]

class UserUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    height: Optional[float] = None
    weight: Optional[float] = None # Tu waga jest potrzebna do update'u
    target_weight: Optional[float] = None
    weekly_goal_kg: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    diet_style: Optional[DietStyle] = None
    calorie_goal: Optional[int] = None
    protein_goal: Optional[int] = None
    fat_goal: Optional[int] = None
    carb_goal: Optional[int] = None
    water_goal: Optional[int] = None
    preferences: Optional[UserPreferences] = None
    add_workout_calories_to_goal: Optional[bool] = None
    is_social_profile_active: Optional[bool] = None
    last_diet_plan: Optional[str] = None
    last_weekly_analysis: Optional[str] = None
    last_analysis_generated_at: Optional[datetime] = None

class User(UserBase):
    id: int
    is_verified: bool
    preferences: Optional[UserPreferences] = None
    diet_plan_requests: int
    last_request_date: date
    weight: Optional[float] = None # Tu waga jest potrzebna do odczytu
    subscription_status: SubscriptionStatus
    subscription_expires_at: Optional[datetime] = None
    goal_achievement_date: Optional[str] = None

    class Config:
        from_attributes = True
        use_enum_values = True

# UserResponse dziedziczy po User, żeby mieć wszystkie pola + wagę
class UserResponse(User):
    pass

# --- ISTNIEJĄCE SCHEMATY ---

class MealEntryBase(BaseModel):
    product_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    weight: float # Dodane, bo jest używane w MealResponse

class MealEntryCreate(MealEntryBase):
    amount: float
    unit: str
    deconstruction_details: Optional[List[Dict[str, Any]]] = None
    display_quantity_text: Optional[str] = None
    is_default_quantity: Optional[bool] = False

class MealEntry(MealEntryBase):
    id: int
    original_amount: float
    original_unit: str
    standardized_grams: float
    meal_id: int
    deconstruction_details: Optional[List[Dict[str, Any]]] = None
    display_quantity_text: Optional[str] = None
    is_default_quantity: Optional[bool] = False
    class Config:
        from_attributes = True

# Uproszczony alias dla Response
class MealEntryResponse(MealEntry):
    pass

class MealBase(BaseModel):
    name: str
    category: MealCategory
    time: Optional[time_class] = None

class MealCreate(MealBase):
    date: date

class Meal(MealBase):
    id: int
    date: date
    entries: List[MealEntry] = []
    class Config:
        from_attributes = True

class MealResponse(Meal):
    pass

class Challenge(BaseModel):
    id: int
    title: str
    description: str
    duration_days: int
    category: str

class UserChallenge(BaseModel):
    id: int
    user_id: int
    challenge_id: int
    status: ChallengeStatus
    start_date: date
    end_date: date
    challenge_info: Optional[Challenge] = None
    class Config:
        from_attributes = True
        use_enum_values = True
        
class WaterEntryBase(BaseModel):
    amount: int

class WaterEntryCreate(WaterEntryBase):
    date: date
    time: Optional[time_class] = None

class WaterEntry(WaterEntryBase):
    id: int
    date: date
    time: time_class
    class Config:
        from_attributes = True

class WorkoutBase(BaseModel):
    name: str
    calories_burned: int

class WorkoutCreate(WorkoutBase):
    date: date
    text: Optional[str] = None
    manual_calories: Optional[int] = None

class Workout(WorkoutBase):
    id: int
    date: date
    class Config:
        from_attributes = True

class WorkoutResponse(Workout):
    pass
        
class AnalysisResponse(BaseModel):
    aggregated_meal: Dict[str, Any]
    deconstruction_details: List[Dict[str, Any]]

# --- POZOSTAŁE SCHEMATY ---

class UserPublic(BaseModel):
    id: int
    name: Optional[str] = None
    email: EmailStr

    class Config:
        from_attributes = True

class CompletedChallengeBadge(BaseModel):
    title: str
    end_date: date

    class Config:
        from_attributes = True
        
class FriendInfo(UserPublic):
    friendship_status: Optional[FriendshipStatus] = None
    completed_challenges: List[CompletedChallengeBadge] = []

class FriendWithBadges(UserPublic):
    completed_challenges: List[CompletedChallengeBadge] = []

class GoalSuggestionRequest(BaseModel):
    gender: Gender
    date_of_birth: date
    height: float
    weight: float
    target_weight: float
    weekly_goal_kg: float
    activity_level: ActivityLevel
    diet_style: DietStyle

class DeconstructedComponent(BaseModel):
    name: str
    quantity_grams: int
    calories: float
    protein: float
    fat: float
    carbs: float
    display_quantity_text: Optional[str] = None
    is_default_quantity: Optional[bool] = False

class DietPlanSuggestionProduct(BaseModel):
    name: str
    quantity_grams: int
    calories: float
    protein: float
    fat: float
    carbs: float
    display_quantity_text: Optional[str] = None
    
class DietPlanSuggestion(BaseModel):
    meal_name: str
    category: MealCategory
    products: List[DietPlanSuggestionProduct]
    recipe: str

class MacroSuggestion(BaseModel):
    calorie_goal: int
    protein_goal: int
    fat_goal: int
    carb_goal: int

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class AnalysisGenerateRequest(BaseModel):
    start_date: date
    end_date: date

class WeeklyAnalysisResponse(BaseModel):
    ai_coach_summary: str
    avg_macros: Dict[str, float]
    total_workouts: int
    total_calories_burned: int
    weight_chart_data: Dict[str, List[Any]]
    analysis_start_date: date
    analysis_end_date: date

class AnalysisDataResponse(BaseModel):
    avg_macros: Dict[str, float]
    total_workouts: int
    total_calories_burned: int
    weight_chart_data: Dict[str, List[Any]]
    analysis_start_date: date
    analysis_end_date: date

class DailySummary(BaseModel):
    date: date
    calories_consumed: float
    protein_consumed: float
    fat_consumed: float
    carbs_consumed: float
    water_consumed: int
    calories_burned: int
    calorie_goal: int
    protein_goal: int
    fat_goal: int
    carb_goal: int
    water_goal: int
    meals: List[Meal]
    water_entries: List[WaterEntry]
    workouts: List[Workout]
    total_calories_burned_today: float

class AnalysisRequest(BaseModel):
    text: Optional[str] = None
    image_base64: Optional[str] = None
    meal_category: Optional[str] = "Inne" # Zmieniono na string, żeby uniknąć problemów z walidacją enuma

    @validator('image_base64', always=True)
    def check_text_or_image(cls, v, values):
        if not values.get('text') and not v:
            raise ValueError('Należy podać tekst lub obrazek do analizy.')
        return v

class FriendshipBase(BaseModel):
    friend_id: int

class FriendshipCreate(FriendshipBase):
    pass

class Friendship(BaseModel):
    id: int
    user_id: int
    friend_id: int
    status: FriendshipStatus
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True

class FriendRequestWithUserInfo(Friendship):
    user_info: UserPublic        

# --- NOWE SCHEMATY DLA AKCJI E-MAIL ---
class EmailSchema(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class DaySummary(BaseModel):
    date: date
    
    # To co zjadłeś (policzone z MealEntries)
    calories_consumed: float = 0.0
    protein_consumed: float = 0.0
    fat_consumed: float = 0.0
    carbs_consumed: float = 0.0
    water_consumed: int = 0
    
    # Cele użytkownika (Pobierane z profilu User)
    calorie_goal: int = 2000
    protein_goal: int = 100
    fat_goal: int = 70
    carb_goal: int = 250
    water_goal: int = 2500
    
    # Listy (Any dla bezpieczeństwa przed cyrkulacją, ale można użyć MealResponse)
    meals: List[Any] = []
    workouts: List[Any] = []
    
    total_calories_burned: int = 0
    goal_achievement_date: Optional[str] = None

    class Config:
        from_attributes = True

# --- SEKCJA WAGI ---

class WeightEntryBase(BaseModel):
    weight: float
    date: date

class WeightEntryCreate(WeightEntryBase):
    pass

class WeightEntry(WeightEntryBase):
    id: int
    owner_id: int
    class Config:
        from_attributes = True