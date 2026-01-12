import streamlit as st
import google.generativeai as genai

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="Work Assistant 2.5", page_icon="🚀", layout="centered")

# --- SICHERHEITS-CHECK ---
# Passwort aus Secrets laden
correct_password = st.secrets.get("APP_PASSWORD")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Login Maske
if not st.session_state.authenticated:
    st.title("🔒 Login")
    password_input = st.text_input("Zugangscode eingeben", type="password")
    if st.button("Anmelden"):
        if password_input == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Falsches Passwort")
    st.stop()

# --- HAUPT-ANWENDUNG ---
st.title("🤖 Assistant (Gemini 2.5 Pro)")

# API Key laden
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("API Key fehlt in den Secrets.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    # WICHTIG: Hier nutzen wir exakt das Modell aus deiner Liste
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Verbindungsfehler: {e}")
    st.stop()

# Chat Historie initialisieren
if "messages" not in st.session_state:
    st.session_state.messages = []

# Historie anzeigen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input & Verarbeitung
if prompt := st.chat_input("Wie kann ich helfen?"):
    # 1. User Input anzeigen
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Antwort generieren
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # History für Gemini aufbereiten
            history_gemini = [
                {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
                for m in st.session_state.messages if m["role"] != "system"
            ]
            
            # Chat Session starten (ohne den allerletzten Prompt, den senden wir gleich)
            chat = model.start_chat(history=history_gemini[:-1])
            
            # Stream response (sieht cooler aus, wie beim echten ChatGPT)
            response = chat.send_message(prompt, stream=True)
            
            full_response = ""
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # Antwort speichern
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            message_placeholder.error(f"Fehler: {e}")
