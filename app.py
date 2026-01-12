import streamlit as st
import speech_recognition as sr
from gtts import gTTS
from groq import Groq
import os
from pydub import AudioSegment
import io 

# --- SETUP HALAMAN ---
st.set_page_config(page_title="AI Chat Bilingual", page_icon="🤖")
st.title("🤖 AI Chat: Bilingual (ID/EN)")

# --- SESSION STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_mic_id" not in st.session_state:
    st.session_state.last_mic_id = None

# --- SETUP API KEY (GROQ) ---
api_key = st.secrets["GROQ_API_KEY"]
try:
    client = Groq(api_key=api_key)
except Exception as e:
    st.error(f"API Key bermasalah: {e}")

# --- FUNGSI 1: OTAK AI (DINAMIS) ---
def ai_think(text_input, language_mode):
    # Tentukan instruksi berdasarkan bahasa yang dipilih
    if language_mode == 'en':
        system_instruction = (
            "You are a smart, polite, and cool AI assistant. "
            "You MUST reply in English. "
            "Keep your answer concise (max 2-3 sentences)."
        )
    else:
        system_instruction = (
            "Kamu adalah asisten AI yang cerdas, sopan, dan gaul. "
            "Kamu HARUS menjawab dalam Bahasa Indonesia. "
            "Jawablah dengan ringkas dan padat (maksimal 2-3 kalimat)."
        )

    try:
        messages_payload = [{"role": "system", "content": system_instruction}]
        
        # Ingatan chat
        for msg in st.session_state.chat_history[-5:]:
            messages_payload.append({"role": msg["role"], "content": msg["content"]})
        
        messages_payload.append({"role": "user", "content": text_input})

        chat_completion = client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error processing request: {e}"

# --- FUNGSI 2: PROSES AUDIO (CERDAS BAHASA) ---
def process_audio_source(audio_file_path, lang_code_full, source_type="mic"):
    r = sr.Recognizer()
    
    # Ekstrak kode bahasa pendek untuk gTTS & Logika AI
    # Contoh: 'id-ID' -> 'id', 'en-US' -> 'en'
    lang_code_short = lang_code_full.split('-')[0]

    try:
        if not os.path.exists(audio_file_path):
            st.error("File audio error.")
            return

        with sr.AudioFile(audio_file_path) as source:
            if source_type == "mic":
                r.adjust_for_ambient_noise(source, duration=0.5)
            
            audio_data = r.record(source)
            
            try:
                # STT: Mendengar sesuai setting bahasa
                input_text = r.recognize_google(audio_data, language=lang_code_full)
            except sr.UnknownValueError:
                st.warning("Suara tidak jelas / hening.")
                return
            except sr.RequestError:
                st.error("Koneksi Google Speech error.")
                return
        
        # Tampilkan Input User
        with st.chat_message("user"):
            st.markdown(f"**🗣️ Input ({lang_code_short.upper()}):** {input_text}")
        
        st.session_state.chat_history.append({"role": "user", "content": input_text})

        # AI Menjawab
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Kirim kode bahasa ke otak AI agar jawabannya sesuai
                response_text = ai_think(input_text, lang_code_short)
                st.markdown(response_text)
                
                # TTS: Bicara sesuai bahasa jawaban
                try:
                    # Parameter 'lang' diisi dinamis (id atau en)
                    tts = gTTS(text=response_text, lang=lang_code_short)
                    mp3_fp = io.BytesIO()
                    tts.write_to_fp(mp3_fp)
                    mp3_fp.seek(0)
                    
                    st.audio(mp3_fp, format='audio/mp3', autoplay=True)
                except Exception as e:
                    st.error(f"Gagal memutar suara: {e}")
        
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})

    except Exception as e:
        st.error(f"Error sistem: {e}")

# --- UI: SIDEBAR ---
st.sidebar.header("⚙️ Settings / Pengaturan")
st.sidebar.write("Pilih bahasa percakapan:")

# Dropdown penentu nasib (Inggris atau Indo)
bahasa_pilihan = st.sidebar.selectbox(
    "Bahasa (Language):",
    ("Indonesia (id-ID)", "English (en-US)"),
    index=0
)

# Ambil kode lengkap (misal: id-ID)
kode_bahasa = bahasa_pilihan.split("(")[1].replace(")", "")

# --- UI: HISTORY CHAT ---
container = st.container()
with container:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

st.divider()

# --- UI: INPUT TABS ---
tab_mic, tab_upload = st.tabs(["🎤 Live Record", "📂 Upload File"])

# === TAB 1: MIC ===
with tab_mic:
    st.write(f"Rekam suara ({'Bahasa Indonesia' if 'id' in kode_bahasa else 'English'}):")
    audio_mic = st.audio_input("Mulai bicara...", key="mic_input")
    
    if audio_mic:
        if audio_mic != st.session_state.last_mic_id:
            st.session_state.last_mic_id = audio_mic
            
            with st.spinner("Processing..."):
                try:
                    temp_raw = "temp_mic_raw"
                    clean_wav = "temp_mic_clean.wav"
                    
                    with open(temp_raw, "wb") as f:
                        f.write(audio_mic.getvalue())
                    
                    sound = AudioSegment.from_file(temp_raw)
                    sound = sound.set_channels(1).set_frame_rate(16000)
                    sound.export(clean_wav, format="wav")
                    
                    # Panggil fungsi proses dengan bahasa yang dipilih
                    process_audio_source(clean_wav, kode_bahasa, source_type="mic")
                    
                    try:
                        os.remove(temp_raw)
                        os.remove(clean_wav)
                    except:
                        pass
                except Exception as e:
                    st.error(f"Error: {e}")

# === TAB 2: UPLOAD ===
with tab_upload:
    st.write("Upload file audio:")
    uploaded_file = st.file_uploader("File (MP3/WAV)", type=['mp3', 'wav'], key="file_input")
    
    if uploaded_file is not None:
        if st.button("▶️ Proses", type="primary"):
            with st.spinner("Processing..."):
                try:
                    temp_filename = "temp_upload_raw"
                    final_wav = "temp_upload_ready.wav"
                    
                    with open(temp_filename, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    if uploaded_file.name.endswith('.mp3'):
                        sound = AudioSegment.from_mp3(temp_filename)
                    else:
                        sound = AudioSegment.from_wav(temp_filename)

                    sound = sound.set_channels(1).set_frame_rate(16000)
                    if len(sound) > 60000:
                        sound = sound[:60000]

                    sound.export(final_wav, format="wav")

                    # Panggil fungsi proses dengan bahasa yang dipilih
                    process_audio_source(final_wav, kode_bahasa, source_type="file")

                    try:
                        os.remove(temp_filename)
                        os.remove(final_wav)
                    except:
                        pass
                except Exception as e:

                    st.error(f"Error: {e}")

