import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic
import random

# Inicializar buscador de YouTube Music
@st.cache_resource
def get_ytmusic():
    try:
        return YTMusic()
    except Exception:
        return None

ytmusic = get_ytmusic()

# Configuración de la página
st.set_page_config(page_title="MusicNow", layout="centered")

# CSS Global
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');

    .stApp { 
        background-color: #0e0e10; 
        color: #ffffff; 
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 680px !important;
    }

    .minimal-title {
        font-family: 'Inter', sans-serif;
        color: #ff2222;
        text-align: center;
        font-size: 3.8rem;
        font-weight: 900;
        margin-bottom: 4px;
        letter-spacing: -1.5px;
    }
    
    .minimal-sub-wave {
        font-family: 'Inter', sans-serif;
        text-align: center;
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 22px;
        letter-spacing: -0.2px;
        background: linear-gradient(90deg, #ff2222 0%, #ff2222 20%, #ff6b00 32%, #00f0ff 42%, #a855f7 52%, #ec4899 62%, #ff2222 75%, #ff2222 100%);
        background-size: 260% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: rgbWaveSweep 3.8s ease-in-out infinite alternate;
    }

    @keyframes rgbWaveSweep {
        0% { background-position: 100% 0%; }
        100% { background-position: 0% 0%; }
    }

    /* Ocultar instrucciones de Streamlit */
    div[data-testid="InputInstructions"], 
    div[data-testid="stInputInstructions"],
    [data-testid="stInputInstructions"],
    [data-testid="InputInstructions"],
    .stTextInputInstructions,
    div[data-testid="stTextInput"] small {
        display: none !important;
    }

    /* BARRA DE BÚSQUEDA Y BOTÓN */
    div[data-testid="stForm"] {
        background-color: #16161a !important;
        border: 2px solid #ff2222 !important;
        border-radius: 14px !important;
        padding: 4px 8px !important;
        box-shadow: 0 0 12px rgba(255, 34, 34, 0.25) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    div[data-testid="stForm"]:focus-within {
        border-color: #ff5555 !important;
        box-shadow: 0 0 18px rgba(255, 34, 34, 0.45) !important;
    }

    div[data-testid="stTextInput"] {
        margin-bottom: 0px !important;
    }

    div[data-testid="stTextInput"] > div > div {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        height: 42px !important;
    }

    div[data-testid="stTextInput"] input {
        background-color: transparent !important;
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.95rem !important;
        padding: 8px 12px !important;
        height: 40px !important;
    }

    div[data-testid="stForm"] button[data-testid="stFormSubmitButton"] {
        height: 40px !important;
        border-radius: 10px !important;
        background-color: #ff2222 !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 0 8px rgba(255, 34, 34, 0.3) !important;
    }

    div[data-testid="stForm"] button[data-testid="stFormSubmitButton"]:hover {
        background-color: #ff4444 !important;
        box-shadow: 0 0 14px rgba(255, 34, 34, 0.6) !important;
    }

    /* BOTONES DE SUGERENCIAS */
    div.stButton > button {
        background-color: #16161a; 
        color: #e0e0e0; 
        font-family: 'Inter', sans-serif;
        font-size: 0.92rem;
        font-weight: 500;
        border: 1px solid #2a2a30; 
        border-radius: 12px; 
        width: 100%; 
        text-align: left; 
        transition: all 0.2s ease;
        padding: 12px 16px;
        margin-bottom: 0px;
    }
    
    div.stButton > button:hover { 
        background-color: #ff2222 !important; 
        border-color: #ff2222 !important; 
        color: #ffffff !important; 
        transform: translateY(-1px);
    }

    /* IMÁGENES DE MINIATURA */
    div[data-testid="stImage"] img {
        border-radius: 8px !important;
        object-fit: cover !important;
    }

    h3 {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-top: 22px !important;
        margin-bottom: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Encabezado principal
st.markdown("<h1 class='minimal-title'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='minimal-sub-wave'>Busca la canción o música que quieras y reprodúcela ahora mismo</p>", 
    unsafe_allow_html=True
)

# Estado global
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
    st.session_state.song_title = None
    st.session_state.artist_name = None
    st.session_state.vinyl_color = "#ff2222"
    st.session_state.thumbnail_url = ""

if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

def obtener_color_aleatorio():
    colores = [
        "#ff2222", "#00f0ff", "#a855f7", "#ec4899", 
        "#ff9500", "#00ff88", "#3b82f6", "#ff206e", 
        "#10b981", "#e11d48", "#8b5cf6", "#f59e0b"
    ]
    return random.choice(colores)

# Configuración del vinilo
label_style = ""
if st.session_state.thumbnail_url:
    label_style = f"background-image: url('{st.session_state.thumbnail_url}'); background-size: cover; background-position: center; border: 2px solid {st.session_state.vinyl_color};"
else:
    label_style = f"background-color: {st.session_state.vinyl_color};"

v_id = st.session_state.video_id or ""
s_title = st.session_state.song_title or ""
s_artist = st.session_state.artist_name or ""
v_color = st.session_state.vinyl_color

html_reproductor_completo = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{
        background-color: transparent; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        margin: 0; 
        padding: 10px 0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: #ffffff;
    }}
    .vinyl {{
        width: 170px; height: 170px; border-radius: 50%; position: relative; 
        display: flex; justify-content: center; align-items: center;
        background: radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
                    repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
                    conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
        box-shadow: 0 8px 22px rgba(0,0,0,0.9), 0 0 20px {v_color};
        border: 1px solid #1a1a1a;
        animation: spin 3s linear infinite;
        margin-bottom: 15px;
    }}
    .center-label {{
        width: 70px; height: 70px; border-radius: 50%;
        display: flex; justify-content: center; align-items: center; z-index: 2;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 0 8px {v_color};
        {label_style}
    }}
    .center-hole {{ 
        width: 10px; height: 10px; background: #ffffff; border-radius: 50%; box-shadow: inset 0 0 2px rgba(0,0,0,0.8);
    }}
    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}

    .player-card {{
        width: 100%;
        max-width: 460px;
        background-color: #16161a;
        border: 1px solid #2a2a30;
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 0 20px rgba(0,0,0,0.6), 0 0 12px {v_color}40;
        box-sizing: border-box;
        text-align: center;
    }}
    .song-details {{
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #ffffff;
    }}
    .iframe-container {{
        position: relative;
        width: 100%;
        padding-top: 56.25%;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        background-color: #000000;
    }}
    .iframe-container iframe {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
    }}
    .external-link {{
        display: inline-block;
        margin-top: 10px;
        font-size: 0.8rem;
        color: #a0a0a0;
        text-decoration: none;
        transition: color 0.2s ease;
    }}
    .external-link:hover {{
        color: #ff2222;
    }}
</style>
</head>
<body>

    <div class="vinyl">
        <div class="center-label"><div class="center-hole"></div></div>
    </div>

    {"<div class='player-card'>" if v_id else "<div style='margin-top:10px; color:#777; font-size:0.9rem;'>Selecciona una canción para comenzar</div>"}
    {"<div class='song-details'>▶ " + s_title + " — " + s_artist + "</div>" if v_id else ""}
    {"<div class='iframe-container'><iframe src='https://www.youtube-nocookie.com/embed/" + v_id + "?autoplay=1&rel=0' title='MusicNow Player' allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share' referrerpolicy='strict-origin-when-cross-origin' allowfullscreen></iframe></div>" if v_id else ""}
    {"<a class='external-link' href='https://www.youtube.com/watch?v=" + v_id + "' target='_blank'>¿No carga el video? Abrir directamente en YouTube ↗</a>" if v_id else ""}
    {"</div>" if v_id else ""}

</body>
</html>
"""

altura_componente = 550 if st.session_state.video_id else 220
components.html(html_reproductor_completo, height=altura_componente)

# ---------------------------------------------------------
# FORMULARIO DE BÚSQUEDA
# ---------------------------------------------------------
with st.form(key="search_form", border=False):
    col_btn, col_input = st.columns([0.18, 0.82], vertical_alignment="center")
    with col_btn:
        btn_buscar = st.form_submit_button("Buscar", use_container_width=True)
    with col_input:
        query_input = st.text_input("Búsqueda", placeholder="Buscar canción, artista o género...", label_visibility="collapsed")

if btn_buscar and query_input.strip():
    st.session_state.current_query = query_input.strip()

# ---------------------------------------------------------
# BÚSQUEDA Y RESULTADOS
# ---------------------------------------------------------
if st.session_state.current_query:
    st.write("### Sugerencias")
    
    if ytmusic is None:
        st.error("No se pudo conectar a YouTube Music.")
    else:
        try:
            resultados = ytmusic.search(st.session_state.current_query, filter="videos", limit=8)
            if not resultados:
                resultados = ytmusic.search(st.session_state.current_query, limit=8)
            
            if not resultados:
                st.info("No se encontraron resultados para tu búsqueda.")
            else:
                for idx, item in enumerate(resultados):
                    v_id = item.get('videoId')
                    if not v_id:
                        continue
                    
                    titulo = item.get('title', 'Canción desconocida')
                    artistas_list = item.get('artists', [])
                    artistas = ", ".join([a['name'] for a in artistas_list if 'name' in a])
                    if not artistas:
                        artistas = item.get('author', 'Artista')
                    
                    duracion = item.get('duration', '')
                    
                    thumbnails = item.get('thumbnails', [])
                    thumb_url = thumbnails[-1]['url'] if thumbnails else ""
                    
                    texto_opcion = f"🎵  {titulo} — {artistas}" + (f" ({duracion})" if duracion else "")
                    
                    col_img, col_btn = st.columns([0.14, 0.86], vertical_alignment="center")
                    with col_img:
                        if thumb_url:
                            st.image(thumb_url, use_container_width=True)
                    with col_btn:
                        if st.button(texto_opcion, key=f"song_{v_id}_{idx}"):
                            st.session_state.video_id = v_id
                            st.session_state.song_title = titulo
                            st.session_state.artist_name = artistas
                            st.session_state.vinyl_color = obtener_color_aleatorio()
                            st.session_state.thumbnail_url = thumb_url
                            st.rerun()
                            
        except Exception as e:
            st.error(f"Error al realizar la búsqueda: {str(e)}")
