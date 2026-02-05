import os
import re
import sounddevice as sd
import numpy as np
import tempfile
import wave
import subprocess
import whisper
import time
import streamlit as st

# --- Asegurar compatibilidad FFmpeg en Windows ---
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"  # Cambia si tu FFmpeg está en otra ruta

# --- Inicializar modelo Whisper una sola vez ---
@st.cache_resource
def cargar_modelo_whisper():
    return whisper.load_model("base")

modelo = cargar_modelo_whisper()


# --- Grabar audio del micrófono ---
def grabar_audio(duracion=30, samplerate=16000):
    """
    Graba audio desde el micrófono y detecta silencio para detenerse antes.
    Implementación sin callbacks para evitar actualizar Streamlit desde otro hilo.
    """
    st.info("🎙️ Grabando... habla ahora (di 'terminar' o guarda silencio para finalizar).")
    progress = st.empty()
    audio_buffer = []

    with sd.InputStream(samplerate=samplerate, channels=1) as stream:
        start_time = time.time()
        silencio_tiempo = 0.0
        frame_duration = 0.2  # segundos por lectura
        frames_per_read = int(samplerate * frame_duration)

        while True:
            data, _ = stream.read(frames_per_read)
            audio_buffer.append(data.copy())

            vol = np.linalg.norm(data)
            barra = "▰" * int(min(vol * 10, 30))
            progress.text(f"[{barra:<30}] {vol:.2f}")

            if vol < 0.005:
                silencio_tiempo += frame_duration
            else:
                silencio_tiempo = 0.0

            if silencio_tiempo > 3 or (time.time() - start_time) > duracion:
                break

    progress.empty()
    st.success("✅ Grabación finalizada.")
    audio = np.concatenate(audio_buffer, axis=0)
    return audio.flatten()


# --- Guardar y transcribir audio ---
def guardar_y_transcribir():
    """
    Graba, guarda temporalmente el audio en WAV y usa Whisper para convertirlo a texto.
    """
    audio = grabar_audio()

    # Asegurar que audio está en formato float32 [-1,1]
    audio = np.asarray(audio)
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)
    if audio.max() > 1.0 or audio.min() < -1.0:
        # Normalizar por si acaso
        max_val = max(abs(audio.max()), abs(audio.min()))
        if max_val > 0:
            audio = audio / max_val

    temp_wav_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            with wave.open(temp_wav, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes((audio * 32767).astype(np.int16).tobytes())

        # --- Transcribir con Whisper ---
        st.info("🧠 Transcribiendo con Whisper...")
        result = modelo.transcribe(temp_wav_path, fp16=False, language="es")
        texto = result.get("text", "")

        # --- Limpiar texto ---
        texto_limpio = limpiar_texto(texto)
        st.success("✅ Transcripción completada.")
        return texto_limpio
    finally:
        try:
            if temp_wav_path and os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)
        except Exception:
            pass


# --- Limpiar muletillas y palabras innecesarias ---
def limpiar_texto(texto):
    """Quita muletillas y normaliza espacios y puntuación manteniendo mayúsculas."""
    muletillas = ["eh", "este", "pues", "o sea", "mmm", "ajá", "em", "ah"]
    pattern = r"\b(?:" + "|".join(re.escape(m) for m in muletillas) + r")\b"
    limpio = re.sub(pattern, "", texto, flags=re.IGNORECASE)
    # Normalizar espacios
    limpio = re.sub(r"\s+", " ", limpio)
    # Quitar espacios antes de comas y puntos sobrantes
    limpio = re.sub(r"\s+,", ",", limpio)
    limpio = re.sub(r",+", ",", limpio)
    return limpio.strip()
