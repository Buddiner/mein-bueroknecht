import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import datetime
from PIL import Image

# --- KONFIGURATION ---
st.set_page_config(page_title="AI Multi-Tool", page_icon="🧠", layout="wide")

# --- WICHTIG: INITIALISIERUNG VOR ALLEM ANDEREN ---
# Wir müssen das Gedächtnis erstellen, BEVOR wir es in der Sidebar nutzen wollen
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SICHERHEITS-CHECK (LOGIN) ---
correct_password = st.secrets.get("APP_PASSWORD")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Login")
    with st.form("login_form"):
        password_input = st.text_input("Zugangscode eingeben", type="password")
        submit_button = st.form_submit_button("Anmelden")
        
    if submit_button:
        if password_input == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Falsches Passwort")
    st.stop()

# --- HAUPT-ANWENDUNG ---
st.title("🤖 Multi-Model Assistant")

# --- SIDEBAR EINSTELLUNGEN ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    
    # 1. Modell Auswahl
    model_option = st.selectbox(
        "Modell wählen:",
        (
            "Gemini 2.5 Flash (FREE)",
            "Gemini 2.5 Pro (Credits)",
            "GPT-4o (Credits)",
            "GPT-4o-mini (Credits)"
        )
    )
    
    st.divider()
    
    # 2. Upload (Nur für Gemini aktiviert)
    uploaded_file = None
    if "Gemini" in model_option:
        uploaded_file = st.file_uploader("Bild analysieren", type=["jpg", "png", "jpeg"])
    else:
        st.info("Bild-Upload aktuell nur für Gemini Modelle aktiv.")

    st.divider()
    
    # 3. Reset & Download
    if st.button("🗑️ Neuer Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    # Download Logik (Funktioniert jetzt, weil messages oben schon erstellt wurde)
    chat_export = ""
    for msg in st.session_state.messages:
        content = msg["content"]
        # Falls Inhalt kein String ist (sondern [Bild, Text]), nehmen wir nur den Text
        if not isinstance(content, str): 
            content = content[1] # Der Text ist das zweite Element in der Liste
        
        chat_export += f"{msg['role'].upper()}: {content}\n\n"
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    st.download_button("💾 Chat speichern", chat_export, file_name=f"chat_{timestamp}.txt")

# --- API KEYS LADEN ---
google_api_key = st.secrets.get("GOOGLE_API_KEY")
openai_api_key = st.secrets.get("OPENAI_API_KEY")

# --- CHAT VERLAUF ANZEIGEN ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            # Wenn Bildinhalt gespeichert wurde (Liste [Bild, Text])
            st.image(message["content"][0], width=300)
            st.markdown(message["content"][1])

# --- INPUT VERARBEITUNG ---
if prompt := st.chat_input("Nachricht eingeben..."):
    
    # User Input anzeigen und speichern
    if uploaded_file and "Gemini" in model_option:
        image = Image.open(uploaded_file)
        # Speichere als Liste [Bild, Text]
        st.session_state.messages.append({"role": "user", "content": [image, prompt]})
        with st.chat_message("user"):
            st.image(image, width=300)
            st.markdown(prompt)
    else:
        # Speichere als Text
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

    # ANTWORT GENERIEREN
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # --- FALL A: GOOGLE GEMINI ---
            if "Gemini" in model_option:
                if not google_api_key:
                    st.error("Google API Key fehlt in Secrets!")
                    st.stop()
                
                genai.configure(api_key=google_api_key)
                
                # Modell-Name mappen
                if "Flash" in model_option:
                    model_name = "gemini-2.5-flash"
                else:
                    model_name = "gemini-2.5-pro" # Fallback auf 2.0-flash wenn 2.5-pro zickt: 'gemini-2.0-flash'
                
                model = genai.GenerativeModel(model_name)
                
                # History für Google aufbereiten (nur Text-Teile für Stabilität)
                gemini_history = []
                for m in st.session_state.messages[:-1]:
                    if isinstance(m["content"], str):
                         gemini_history.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})

                chat = model.start_chat(history=gemini_history)
                
                # Senden (mit oder ohne Bild)
                if uploaded_file:
                    # Wir müssen das Bild-Objekt wieder aus dem Session State holen
                    # Das letzte Element in messages ist unser aktueller Prompt [Bild, Text]
                    last_msg_content = st.session_state.messages[-1]["content"]
                    image_obj = last_msg_content[0]
                    response = chat.send_message([prompt, image_obj], stream=True)
                else:
                    response = chat.send_message(prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")

            # --- FALL B: OPENAI CHATGPT ---
            elif "GPT" in model_option:
                if not openai_api_key:
                    st.error("OpenAI API Key fehlt in Secrets! Bitte nachtragen.")
                    st.stop()
                
                client = OpenAI(api_key=openai_api_key)
                
                # Modell-Name mappen
                gpt_model = "gpt-4o" if "GPT-4o" in model_option and "mini" not in model_option else "gpt-4o-mini"
                
                # History für OpenAI aufbereiten
                openai_messages = []
                for m in st.session_state.messages:
                    # Einfache Text-History (Bilder ignorieren wir hier vorerst für Stabilität)
                    content_str = m["content"]
                    if not isinstance(content_str, str):
                        content_str = content_str[1] # Nur Textteil nehmen
                        
                    openai_messages.append({"role": m["role"], "content": content_str})
                
                stream = client.chat.completions.create(
                    model=gpt_model,
                    messages=openai_messages,
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")

            # Abschluss
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            message_placeholder.error(f"Fehler: {e}")
