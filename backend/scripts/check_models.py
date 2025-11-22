import google.generativeai as genai
import os
import sys

# Dodajemy ścieżkę, żeby pobrać config (klucz API)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.core.config import settings

def list_available_models():
    print("🔍 Sprawdzam dostępne modele Gemini dla Twojego klucza API...")
    
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        print("❌ BŁĄD: Nie znaleziono klucza GOOGLE_API_KEY w .env")
        return

    try:
        genai.configure(api_key=api_key)
        
        # Pobieramy listę modeli
        models = list(genai.list_models())
        
        print("\n✅ OTO LISTA DOSTĘPNYCH MODELI (Kopiuj nazwę dokładnie):")
        print("="*50)
        found_any = False
        for m in models:
            # Filtrujemy tylko te, które potrafią generować tekst (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                print(f" 👉 {m.name}")
                found_any = True
        
        if not found_any:
            print("⚠️ Nie znaleziono żadnych modeli obsługujących 'generateContent'. Sprawdź uprawnienia klucza.")
            
        print("="*50)

    except Exception as e:
        print(f"\n❌ BŁĄD POŁĄCZENIA Z GOOGLE: {e}")
        print("Wskazówka: Sprawdź czy klucz API jest poprawny i czy masz włączone 'Generative Language API' w Google Cloud Console.")

if __name__ == "__main__":
    list_available_models()