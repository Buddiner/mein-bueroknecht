import streamlit as st
import google.generativeai as genai
import datetime
from PIL import Image

# --- 1. LAYOUT AUF "BREIT" STELLEN ---
st.set_page_config(page_title="Work Assistant Pro", page_icon="🚀", layout="wide")

# --- SICHERHEITS-CHECK ---

correct_password = st.secrets.get("APP_PASSWORD")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Login")
    
    # ÄNDERUNG: Wir nutzen st.form, damit "Enter" funktioniert
    with st.form("login_form"):
        password_input = st.text_input("Zugangscode eingeben", type="password")
        # Dieser Button reagiert nun automatisch auf die Enter-Taste im Textfeld
        submit_button = st.form_submit_button("Anmelden")

    if submit_button:
        if password_input == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Falsches Passwort")
            
    st.stop() # Stoppt hier, solange nicht eingeloggt

# --- SETUP ---
st.title("🤖 Assistant Pro (Multimodal)")

api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("API Key fehlt.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash') 
except Exception as e:
    st.error(f"Verbindungsfehler: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR FUNKTIONEN ---
with st.sidebar:
    st.header("Werkzeuge")
    
    # BILD UPLOAD
    uploaded_file = st.file_uploader("Bild analysieren (Screenshot/Diagramm)", type=["jpg", "png", "jpeg"])
    
    st.divider()
    
    if st.button("🗑️ Neuer Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    # DOWNLOAD LOGIK
    chat_export = ""
    for msg in st.session_state.messages:
        role = "ICH" if msg["role"] == "user" else "AI"
        # Wir filtern Bild-Daten aus dem Text-Export heraus
        content_text = msg["content"] if isinstance(msg["content"], str) else "[BILD UPLOAD]"
        chat_export += f"{role}:\n{content_text}\n\n---\n\n"
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    st.download_button("💾 Chat speichern", chat_export, file_name=f"chat_{timestamp}.txt")

# --- CHAT VERLAUF ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Wenn der Inhalt ein String ist, zeige ihn an. Wenn nicht (Bild), zeige Hinweis.
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            st.image(message["content"][0], caption="Hochgeladenes Bild", width=300)

# --- EINGABE & VERARBEITUNG ---
if prompt := st.chat_input("Nachricht eingeben..."):
    
    # 1. User Input vorbereiten
    if uploaded_file:
        # Wenn ein Bild da ist, öffnen wir es mit PIL
        image = Image.open(uploaded_file)
        # Wir speichern das Bild und den Text als Liste für die Anzeige
        user_content_for_display = [image, prompt] # Liste für Streamlit Anzeige
        user_content_for_api = [prompt, image]     # Liste für Gemini API
        
        st.session_state.messages.append({"role": "user", "content": user_content_for_display})
        with st.chat_message("user"):
            st.image(image, width=300)
            st.markdown(prompt)
    else:
        # Nur Text
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

    # 2. Antwort generieren
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # History bauen (Achtung: Bilder in der History sind komplex, 
            # für diese einfache App senden wir Bilder nur im *aktuellen* Turn)
            # Wir nehmen für die History nur Text-Teile der Vergangenheit, um Fehler zu vermeiden
            history_gemini = []
            for m in st.session_state.messages[:-1]:
                if isinstance(m["content"], str):
                     history_gemini.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})
            
            # Chat starten
            chat = model.start_chat(history=history_gemini)
            
            # Nachricht senden (Entweder Text oder Text+Bild)
            if uploaded_file:
                # API Call mit Bild (Image Objekt direkt an Gemini senden)
                response = chat.send_message(user_content_for_api, stream=True)
            else:
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
