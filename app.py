import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import datetime
from PIL import Image

# --- KONFIGURATION ---
st.set_page_config(page_title="AI Multi-Tool", page_icon="🧠", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SICHERHEITS-CHECK ---
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    
    # MODELL-LISTE: Klar gekennzeichnet was gratis ist
    model_map = {
        "🟢 Gemini 2.0 Flash (GRATIS & Stabil)": "gemini-2.0-flash",
        "🟢 Gemini 2.5 Flash (GRATIS & Neu)": "gemini-2.5-flash",
        "🧪 Gemini 3.0 Flash (Preview)": "gemini-3-flash-preview",
        "💲 Gemini 2.5 Pro (Credits nötig)": "gemini-2.5-pro",
        "💲 GPT-4o (OpenAI Credits)": "gpt-4o",
        "💲 GPT-4o-mini (OpenAI Credits)": "gpt-4o-mini"
    }
    
    selected_label = st.selectbox("Modell wählen:", options=list(model_map.keys()))
    selected_model_id = model_map[selected_label]
    
    st.info(f"Technischer Name: `{selected_model_id}`") # Beweis für dich
    
    st.divider()
    
    # Upload & Reset
    uploaded_file = None
    if "gemini" in selected_model_id:
        uploaded_file = st.file_uploader("Bild analysieren", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ Neuer Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Download
    chat_export = ""
    for msg in st.session_state.messages:
        c = msg["content"]
        if not isinstance(c, str): c = c[1]
        chat_export += f"{msg['role'].upper()}: {c}\n\n"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    st.download_button("💾 Chat speichern", chat_export, file_name=f"chat_{timestamp}.txt")

# --- API KEYS ---
google_api_key = st.secrets.get("GOOGLE_API_KEY")
openai_api_key = st.secrets.get("OPENAI_API_KEY")

# --- ANZEIGE ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if isinstance(message["content"], str):
            st.markdown(message["content"])
        else:
            st.image(message["content"][0], width=300)
            st.markdown(message["content"][1])

# --- INPUT & LOGIK ---
if prompt := st.chat_input("Nachricht eingeben..."):
    
    # Speichern
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

    # Antworten
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # --- GOOGLE GEMINI ---
            if "gemini" in selected_model_id:
                if not google_api_key:
                    st.error("Google API Key fehlt!")
                    st.stop()
                
                genai.configure(api_key=google_api_key)
                
                # HIER IST DER TRICK: System Instruction setzen!
                # Wir zwingen das Modell zu wissen, wer es ist.
                sys_instruct = f"Du bist das Modell {selected_label}. Antworte präzise und hilfreich."
                
                model = genai.GenerativeModel(
                    selected_model_id,
                    system_instruction=sys_instruct
                )
                
                # History (Text only)
                gemini_history = []
                for m in st.session_state.messages[:-1]:
                    if isinstance(m["content"], str):
                         gemini_history.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})

                chat = model.start_chat(history=gemini_history)
                
                if uploaded_file:
                    last_content = st.session_state.messages[-1]["content"]
                    response = chat.send_message([prompt, last_content[0]], stream=True)
                else:
                    response = chat.send_message(prompt, stream=True)
                
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")

            # --- OPENAI ---
            elif "gpt" in selected_model_id:
                if not openai_api_key:
                    st.error("OpenAI API Key fehlt!")
                    st.stop()
                
                client = OpenAI(api_key=openai_api_key)
                
                openai_msgs = [{"role": "system", "content": f"Du bist {selected_label}."}]
                for m in st.session_state.messages:
                    c = m["content"]
                    if not isinstance(c, str): c = c[1]
                    openai_msgs.append({"role": m["role"], "content": c})
                
                stream = client.chat.completions.create(
                    model=selected_model_id,
                    messages=openai_msgs,
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            # Spezielle Fehlerbehandlung für das "Pro" Problem
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                st.error("⚠️ QUOTA FEHLER: Dieses Modell (wahrscheinlich Pro) hat keine kostenlose Nutzung mehr. Bitte wechsle auf ein 'Flash' Modell.")
            else:
                st.error(f"Ein Fehler ist aufgetreten: {e}")
