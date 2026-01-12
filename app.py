import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import datetime
from PIL import Image

# --- KONFIGURATION ---
st.set_page_config(page_title="AI Multi-Tool", page_icon="🧠", layout="wide")

# --- INITIALISIERUNG ---
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
    
    # 1. MODELL AUSWAHL (Hier sind die Neuen!)
    # Wir nutzen ein "Dictionary" (Mapping), um den Anzeigenamen mit der technischen ID zu verknüpfen
    model_map = {
        "Gemini 2.5 Flash (FREE)": "gemini-2.5-flash",
        "Gemini 2.5 Pro (CREDITS)": "gemini-2.5-pro",
        "Gemini 3.0 Flash (Preview)": "gemini-3-flash-preview",  # NEU
        "Gemini Flash (Latest FREE)": "gemini-flash-latest",          # NEU
        "GPT-4o (CREDITS)": "gpt-4o",
        "GPT-4o-mini (CREDITS)": "gpt-4o-mini"
    }
    
    selected_label = st.selectbox("Modell wählen:", options=list(model_map.keys()))
    
    # Die echte ID für den Code holen (z.B. "gemini-3-flash-preview")
    selected_model_id = model_map[selected_label]
    
    st.divider()
    
    # 2. Upload (Nur für Gemini)
    uploaded_file = None
    if "gemini" in selected_model_id:
        uploaded_file = st.file_uploader("Bild analysieren", type=["jpg", "png", "jpeg"])
    else:
        st.info("Bild-Upload nur bei Gemini aktiv.")

    st.divider()
    
    # 3. Reset & Download
    if st.button("🗑️ Neuer Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    chat_export = ""
    for msg in st.session_state.messages:
        content = msg["content"]
        if not isinstance(content, str): content = content[1] # Text aus Liste holen
        chat_export += f"{msg['role'].upper()}: {content}\n\n"
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    st.download_button("💾 Chat speichern", chat_export, file_name=f"chat_{timestamp}.txt")

# --- API KEYS ---
google_api_key = st.secrets.get("GOOGLE_API_KEY")
openai_api_key = st.secrets.get("OPENAI_API_KEY")

# --- CHAT VERLAUF ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            st.image(message["content"][0], width=300)
            st.markdown(message["content"][1])

# --- INPUT ---
if prompt := st.chat_input("Nachricht eingeben..."):
    
    # User Input speichern
    if uploaded_file and "gemini" in selected_model_id:
        image = Image.open(uploaded_file)
        st.session_state.messages.append({"role": "user", "content": [image, prompt]})
        with st.chat_message("user"):
            st.image(image, width=300)
            st.markdown(prompt)
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

    # ANTWORT
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # --- FALL A: GOOGLE GEMINI ---
            if "gemini" in selected_model_id:
                if not google_api_key:
                    st.error("Google API Key fehlt!")
                    st.stop()
                
                genai.configure(api_key=google_api_key)
                
                # Wir nutzen hier direkt die ID aus der Sidebar-Auswahl
                model = genai.GenerativeModel(selected_model_id)
                
                # History (Nur Text)
                gemini_history = []
                for m in st.session_state.messages[:-1]:
                    if isinstance(m["content"], str):
                         gemini_history.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})

                chat = model.start_chat(history=gemini_history)
                
                if uploaded_file:
                    last_msg_content = st.session_state.messages[-1]["content"]
                    response = chat.send_message([prompt, last_msg_content[0]], stream=True)
                else:
                    response = chat.send_message(prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")

            # --- FALL B: OPENAI CHATGPT ---
            elif "gpt" in selected_model_id:
                if not openai_api_key:
                    st.error("OpenAI API Key fehlt!")
                    st.stop()
                
                client = OpenAI(api_key=openai_api_key)
                
                openai_messages = []
                for m in st.session_state.messages:
                    content_str = m["content"]
                    if not isinstance(content_str, str): content_str = content_str[1]
                    openai_messages.append({"role": m["role"], "content": content_str})
                
                stream = client.chat.completions.create(
                    model=selected_model_id, # Hier nutzen wir auch direkt die ID
                    messages=openai_messages,
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            message_placeholder.error(f"Fehler: {e}")
