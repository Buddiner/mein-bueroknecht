import streamlit as st
import google.generativeai as genai

st.title("🛠️ Diagnose-Modus")

# 1. API Key holen
api_key = st.secrets.get("GOOGLE_API_KEY")
st.write(f"API Key Status: {'✅ Vorhanden' if api_key else '❌ Fehlt'}")

if api_key:
    try:
        # 2. Konfigurieren
        genai.configure(api_key=api_key)
        
        st.write("Frage Google nach verfügbaren Modellen...")
        
        # 3. Modelle auflisten
        found_models = []
        for m in genai.list_models():
            # Wir suchen nur Modelle, die Text generieren können (chatten)
            if 'generateContent' in m.supported_generation_methods:
                found_models.append(m.name)
        
        if found_models:
            st.success("Erfolg! Folgende Modelle sind verfügbar:")
            for model_name in found_models:
                # Zeige den exakten Namen an, den wir brauchen
                st.code(model_name, language="text")
        else:
            st.warning("Verbindung steht, aber keine Chat-Modelle gefunden. Prüfe den API Key in AI Studio.")
            
    except Exception as e:
        st.error("❌ Schwerer Fehler bei der Verbindung:")
        st.error(e)
