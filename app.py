import streamlit as st
from datetime import datetime, timedelta
from db import init_db, crear_usuario, validar_usuario, obtener_consecutivo, guardar_historia, obtener_historias_por_estado
import google.generativeai as genai
import json
from utils_audio import guardar_y_transcribir

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Historias Clínicas - Ambulancia IA", page_icon="🚑", layout="wide")
init_db()

# --- CONFIGURACIÓN GEMINI ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- FUNCIÓN IA CORRECTORA ---
def analizar_con_gemini(texto: str):
    prompt = f"""
    Eres un asistente médico de ambulancia experto en dictados clínicos.
    Corrige el texto en español latino médico y extrae:
    paciente, edad, motivo, diagnóstico y tratamiento.
    Devuelve **solo un JSON válido** con este formato:

    {{
      "texto_corregido": "Texto corregido con sentido clínico",
      "paciente": "Nombre del paciente o 'No especificado'",
      "edad": número entero o 0,
      "motivo": "Motivo de atención",
      "diagnostico": "Diagnóstico probable",
      "tratamiento": "Tratamiento realizado"
    }}

    Texto a analizar:
    \"\"\"{texto}\"\"\"
    """

    modelos = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    for modelo_id in modelos:
        try:
            modelo = genai.GenerativeModel(modelo_id)
            respuesta = modelo.generate_content(prompt, generation_config={"temperature": 0.3})
            salida = respuesta.text.strip()

            # Extraer JSON puro
            if "{" in salida and "}" in salida:
                salida = salida[salida.find("{"):salida.rfind("}") + 1]

            # Validar JSON
            try:
                json.loads(salida)
                return salida
            except json.JSONDecodeError:
                salida = salida.replace("'", '"').replace(",}", "}").replace(",]", "]")
                json.loads(salida)
                return salida

        except Exception as e:
            st.warning(f"⚠️ {modelo_id} falló: {str(e)[:80]}")
            continue

    st.error("❌ No se pudo procesar con los modelos disponibles.")
    raise RuntimeError("Fallo en análisis IA.")


# --- ESTILOS ---
st.markdown("""
<style>
    * {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;}
    .main {background: linear-gradient(135deg, #f7f9fc 0%, #e8f0f7 100%);}
    .titulo-principal {
        font-size: 32px; 
        font-weight: 700; 
        color: #1a3a52;
        text-align: center;
        margin: 20px 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .seccion {
        background-color: white; 
        padding: 25px; 
        border-radius: 12px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 4px solid #2B547E;
        margin: 15px 0;
    }
    .stButton > button {
        background-color: #2B547E !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background-color: #1a3a52 !important;
        box-shadow: 0 4px 12px rgba(43, 84, 126, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)


# --- LOGIN ---
if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""
if "grabando" not in st.session_state:
    st.session_state.grabando = False  # 🔴 Control del botón toggle de grabación

if not st.session_state.logueado:
    st.markdown("<p class='titulo-principal'>🚑 Sistema de Historias Clínicas - Ambulancia</p>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='seccion'>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            usuario = st.text_input("👤 Usuario", key="login_usuario")
        with col2:
            contrasena = st.text_input("🔒 Contraseña", type="password", key="login_pass")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Iniciar sesión", use_container_width=True):
                if usuario and contrasena:
                    if validar_usuario(usuario, contrasena):
                        st.session_state.logueado = True
                        st.session_state.usuario = usuario
                        st.success("✅ Inicio de sesión exitoso")
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
                else:
                    st.warning("⚠️ Completa todos los campos")

        with col2:
            if st.button("Crear cuenta", use_container_width=True):
                if usuario and contrasena:
                    crear_usuario(usuario, contrasena)
                    st.success("✅ Usuario creado correctamente")
                else:
                    st.warning("⚠️ Completa todos los campos")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2966/2966481.png", width=90)
    st.sidebar.markdown(f"**👋 Bienvenido, {st.session_state.usuario}**")
    opcion = st.sidebar.radio("📋 Menú principal", ["Nueva historia", "Historias incompletas", "Historias completadas", "Cerrar sesión"])

    if opcion == "Cerrar sesión":
        st.session_state.logueado = False
        st.rerun()

    elif opcion == "Nueva historia":
        st.markdown("<p class='titulo-principal'>🩺 Nueva Historia Clínica</p>", unsafe_allow_html=True)
        st.markdown("<div class='seccion'>", unsafe_allow_html=True)

        # Helper para resetear solo los campos del formulario sin cerrar sesión
        def reset_form():
            keys = [
                "paciente_auto", "edad_auto", "motivo_auto", "diagnostico_auto", "tratamiento_auto",
                "texto_corregido", "texto_libre", "paciente", "edad", "motivo_text", "diag_text", "trat_text"
            ]
            for k in keys:
                if k in st.session_state:
                    del st.session_state[k]

        consecutivo = obtener_consecutivo()
        st.write(f"**Consecutivo:** {consecutivo}")

        col1, col2 = st.columns(2)
        with col1:
            paciente = st.text_input("👨‍⚕️ Nombre del paciente", value=st.session_state.get("paciente_auto", ""))
            edad = st.text_input("🎂 Edad", value=st.session_state.get("edad_auto", ""))
        with col2:
            motivo = st.text_area("📋 Motivo de atención", value=st.session_state.get("motivo_auto", ""), height=100, key="motivo_text")
            diagnostico = st.text_area("💊 Diagnóstico", value=st.session_state.get("diagnostico_auto", ""), height=100, key="diag_text")

        tratamiento = st.text_area("🩹 Tratamiento realizado", value=st.session_state.get("tratamiento_auto", ""), height=100, key="trat_text")

        if "texto_corregido" in st.session_state:
            st.text_area("🧾 Texto corregido por IA", st.session_state["texto_corregido"], height=120, disabled=True)

        st.divider()

        # --- BOTÓN DE GRABACIÓN TOGGLE ---
        col_audio, col_text = st.columns([1, 1])
        with col_audio:
            if not st.session_state.grabando:
                if st.button("🎤 Iniciar grabación", use_container_width=True):
                    st.session_state.grabando = True
                    st.info("🎙️ Grabando... presiona el botón nuevamente para detener.")
                    st.rerun()
            else:
                if st.button("🛑 Detener grabación", use_container_width=True):
                    with st.spinner("Procesando audio..."):
                        try:
                            texto_transcrito = guardar_y_transcribir()
                            st.session_state["texto_libre"] = texto_transcrito

                            # --- Envío automático a la IA ---
                            try:
                                resultado = analizar_con_gemini(texto_transcrito)
                                datos = json.loads(resultado)

                                # Llenar los campos automáticamente
                                st.session_state["paciente_auto"] = datos.get("paciente", "")
                                st.session_state["edad_auto"] = str(datos.get("edad", ""))
                                st.session_state["motivo_auto"] = datos.get("motivo", "")
                                st.session_state["diagnostico_auto"] = datos.get("diagnostico", "")
                                st.session_state["tratamiento_auto"] = datos.get("tratamiento", "")
                                st.session_state["texto_corregido"] = datos.get("texto_corregido", "")

                                st.success("✅ Transcripción y análisis completados")
                            except Exception as e:
                                st.error(f"Error al analizar con IA: {str(e)[:120]}")

                        except Exception as e:
                            st.error(f"Error al grabar o transcribir: {str(e)[:120]}")
                        finally:
                            st.session_state.grabando = False
                            st.rerun()

        texto_libre = st.text_area("🎙️ Dictado / Texto libre para IA",
                                   value=st.session_state.get("texto_libre", ""),
                                   placeholder="Escribe o dicta la descripción completa...",
                                   height=150,
                                   key="texto_libre")

        col_analyze, _ = st.columns([1, 3])
        with col_analyze:
            if st.button("🔎 Analizar con IA", use_container_width=True):
                texto = st.session_state.get("texto_libre", "")
                if texto:
                    with st.spinner("Analizando con IA..."):
                        try:
                            resultado = analizar_con_gemini(texto)
                            datos = json.loads(resultado)

                            st.session_state["paciente_auto"] = datos.get("paciente", "")
                            st.session_state["edad_auto"] = str(datos.get("edad", ""))
                            st.session_state["motivo_auto"] = datos.get("motivo", "")
                            st.session_state["diagnostico_auto"] = datos.get("diagnostico", "")
                            st.session_state["tratamiento_auto"] = datos.get("tratamiento", "")
                            st.session_state["texto_corregido"] = datos.get("texto_corregido", "")

                            st.success("✅ Análisis completado y campos auto-llenados")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al analizar con IA: {str(e)[:120]}")
                else:
                    st.warning("⚠️ Ingresa o dicta texto antes de analizar.")

        st.divider()
        if st.button("💾 Guardar historia", use_container_width=True):
            if paciente and edad and motivo:
                try:
                    guardar_historia(consecutivo, st.session_state.usuario, paciente, edad, motivo, diagnostico, tratamiento)
                    st.success("✅ Historia guardada correctamente")
                    reset_form()
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)[:120]}")
            else:
                st.warning("⚠️ Completa los campos obligatorios")

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        estado = "incompleta" if opcion == "Historias incompletas" else "completa"
        historias = obtener_historias_por_estado(st.session_state.usuario, estado)

        st.markdown(f"<p class='titulo-principal'>📂 Historias {estado.capitalize()}</p>", unsafe_allow_html=True)
        if historias:
            for hist in historias:
                st.markdown("<div class='seccion'>", unsafe_allow_html=True)
                st.write(f"**Consecutivo:** {hist[0]}")
                st.write(f"**Paciente:** {hist[2]}")
                st.write(f"**Edad:** {hist[3]}")
                st.write(f"**Motivo:** {hist[4]}")
                st.write(f"**Diagnóstico:** {hist[5]}")
                st.write(f"**Tratamiento:** {hist[6]}")
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No hay historias para mostrar.")
