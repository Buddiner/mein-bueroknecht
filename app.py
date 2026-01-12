import streamlit as st
import google.generativeai as genai
import datetime

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="Work Assistant", page_icon="🚀", layout="centered")

# --- SICHERHEITS-CHECK ---
correct_password = st.secrets.get("APP_PASSWORD")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

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
st.title("🤖 Assistant (Gemini 2.5 Flash)")

# API Key laden
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("API Key fehlt.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    # Dein funktionierendes Modell:
    model = genai.GenerativeModel('gemini-2.5-flash') 
except Exception as e:
    st.error(f"Verbindungsfehler: {e}")
    st.stop()

# Chat Historie initialisieren
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR (DIE NEUE FUNKTION) ---
with st.sidebar:
    st.header("Verwaltung")
    
    # 1. Neuer Chat Button
    if st.button("🗑️ Neuer Chat starten", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # 2. Download Button
    # Wir wandeln den Chat in einen simplen Text um
    chat_export = ""
    for msg in st.session_state.messages:
        role = "ICH" if msg["role"] == "user" else "AI"
        chat_export += f"{role}:\n{msg['content']}\n\n---\n\n"
    
    # Zeitstempel für den Dateinamen
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    st.download_button(
        label="💾 Chat speichern (.txt)",
        data=chat_export,
        file_name=f"chat_verlauf_{timestamp}.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    st.info("Hinweis: Da dies eine Cloud-App ist, wird der Chat gelöscht, wenn du den Tab schließt. Speichere wichtige Infos!")

# --- CHAT VERLAUF ANZEIGEN ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- INPUT ---
if prompt := st.chat_input("Wie kann ich helfen?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            history_gemini = [
                {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
                for m in st.session_state.messages if m["role"] != "system"
            ]
            chat = model.start_chat(history=history_gemini[:-1])
            response = chat.send_message(prompt, stream=True)
            
            full_response = ""
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            message_placeholder.error(f"Fehler: {e}")
