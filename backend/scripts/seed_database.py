import json
import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy import text

# 1. Ustawienie ścieżek
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal, engine, Base
# Importujemy modele dokładnie tak, jak są zdefiniowane w Twoim pliku
from app.models.sql_models import Product, Dish, DishIngredient
# Musimy zaimportować Enum, bo model Product go używa
from app.models.enums import ProductState

DATA_FILENAME = "enriched_master_data.json"

def seed_database():
    print(f"🌱 Rozpoczynam zasiewanie bazy danych (Wersja Full)...")

    # 2. Reset Bazy (Dla pewności, że struktura tabel będzie zgodna z nowym modelem)
    print("🧹 Odświeżanie schematu bazy...")
    try:
        # Usuwamy stare tabele, żeby SQLAlchemy stworzyło je na nowo z poprawnymi kolumnami
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        print(f"⚠️ Info: {e}")
    
    print("🏗️ Tworzenie tabel...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()

    # 3. Wczytanie pliku JSON
    json_path = os.path.join(os.path.dirname(__file__), DATA_FILENAME)
    if not os.path.exists(json_path):
        print(f"❌ Błąd: Brak pliku {DATA_FILENAME} w folderze scripts/")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📦 Wczytano {len(data)} pozycji z pliku.")

    # 4. Separacja: Produkty Proste vs Dania Złożone
    products_cache = {} 
    dishes_to_process = []

    # --- FAZA 1: PRODUKTY PODSTAWOWE ---
    print("⚙️ Przetwarzanie produktów podstawowych...")
    
    for item in data:
        name = item.get('name')
        if not name: continue

        # Jeśli ma dekonstrukcję, to Danie (zajmiemy się nim w Fazie 2)
        if "deconstruction" in item and item["deconstruction"]:
            dishes_to_process.append(item)
        
        # Ale... składniki dań też muszą być w bazie jako Produkty!
        # Więc każdy wpis z JSONa, który ma makro, traktujemy też jako Produkt
        nutrients = item.get('nutrients_per_100g') or item.get('nutrients_per_100ml')
        
        if nutrients:
            # Wykrywanie stanu (stały/płynny)
            state_str = item.get('state', 'solid')
            state_enum = ProductState.LIQUID if state_str == 'liquid' else ProductState.SOLID

            p = Product(
                name=name,
                aliases=item.get('aliases', []), # JSON
                nutrients=nutrients,             # JSON (Kluczowa zmiana!)
                state=state_enum,                # Enum
                average_weight_g=item.get('average_weight_g', 0)
            )
            
            # Dodajemy do sesji tylko jeśli nie ma duplikatu w tym rzucie
            if name.lower() not in products_cache:
                db.add(p)
                products_cache[name.lower()] = p

    db.commit()
    print(f"✅ Zapisano {len(products_cache)} produktów podstawowych.")

    # --- FAZA 2: DANIA ZŁOŻONE ---
    print(f"🍳 Przetwarzanie {len(dishes_to_process)} dań złożonych...")
    
    # Musimy pobrać ID produktów z bazy, bo commit nadał im ID
    saved_products = db.query(Product).all()
    # Mapa: nazwa (lowercase) -> ID
    product_map = {p.name.lower(): p.id for p in saved_products}

    count_dishes = 0
    for dish_data in dishes_to_process:
        dish_name = dish_data['name']
        
        # Tworzymy Danie
        new_dish = Dish(
            name=dish_name,
            category=dish_data.get('category', {}).get('name') if isinstance(dish_data.get('category'), dict) else "Dania",
            aliases=dish_data.get('aliases', [])
        )
        db.add(new_dish)
        db.flush() # Nadaje ID dla new_dish

        # Dodajemy składniki (DishIngredient)
        for ing in dish_data.get("deconstruction", []):
            ing_name = ing.get('ingredient_name', '')
            weight = ing.get('weight_g', 0)
            
            # Szukamy ID składnika w naszych produktach
            prod_id = product_map.get(ing_name.lower())
            
            if prod_id:
                db.add(DishIngredient(
                    dish_id=new_dish.id, 
                    product_id=prod_id, 
                    weight_g=weight
                ))
            else:
                # Jeśli brakuje składnika bazowego (np. 'woda'), 
                # w idealnym świecie powinniśmy go stworzyć.
                # Tutaj logujemy brak, żebyś wiedział.
                # print(f"   ⚠️ Brak składnika '{ing_name}' dla dania '{dish_name}'")
                pass
        
        count_dishes += 1

    db.commit()
    db.close()
    print(f"🚀 Sukces! Baza zasilona: {len(products_cache)} produktów, {count_dishes} dań.")

if __name__ == "__main__":
    seed_database()