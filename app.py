import streamlit as st
import google.generativeai as genai
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="Mein AI Helfer", page_icon="🚀")

# --- SICHERHEITS-CHECK ---
# Wir holen das Passwort aus den "Secrets" (dazu gleich mehr)
# Wenn kein Passwort gesetzt ist, nehmen wir ein Standardpasswort (nicht empfohlen)
correct_password = st.secrets.get("APP_PASSWORD", "Start123")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # Zeige nur das Login-Feld
    st.title("🔒 Login erforderlich")
    password_input = st.text_input("Zugangscode eingeben", type="password")
    if st.button("Anmelden"):
        if password_input == correct_password:
            st.session_state.authenticated = True
            st.rerun() # Seite neu laden nach Login
        else:
            st.error("Falsches Passwort")
    st.stop() # Hier bricht das Skript ab, wenn nicht eingeloggt

# --- HAUPT-ANWENDUNG (Nur sichtbar nach Login) ---
st.title("🤖 Mein Büro-Assistent")

# API Key sicher laden
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("API Key fehlt in den Secrets!")
    st.stop()

# Gemini Konfigurieren
try:
    genai.configure(api_key=api_key)
    # Hier nutzen wir das Pro Modell
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"Fehler bei der Verbindung: {e}")
    st.stop()

# Chat Historie initialisieren
if "messages" not in st.session_state:
    st.session_state.messages = []

# Verlauf anzeigen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Eingabefeld
if prompt := st.chat_input("Was gibt's zu tun?"):
    # User Nachricht speichern und anzeigen
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Antwort generieren
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # History für Gemini aufbereiten
            history_gemini = [
                {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
                for m in st.session_state.messages if m["role"] != "system"
            ]
            
            # Chat starten (nutze history ohne die allerletzte Nachricht, die schicken wir jetzt)
            chat = model.start_chat(history=history_gemini[:-1])
            response = chat.send_message(prompt)
            
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            message_placeholder.error(f"Ein Fehler ist aufgetreten: {e}")
