import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic
import hashlib

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

# CSS Global estilizado
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

    /* ELIMINACIÓN DE INSTRUCCIONES "PRESS ENTER TO APPLY" */
    div[data-testid="InputInstructions"], 
    div[data-testid="stInputInstructions"],
    [data-testid="stInputInstructions"],
    [data-testid="InputInstructions"],
    .stTextInputInstructions,
    div[data-testid="stTextInput"] small,
    div[data-testid="stTextInput"] [data-testid="InputInstructions"],
    div[data-baseweb="popover"],
    div[data-baseweb="tooltip"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        position: absolute !important;
        pointer-events: none !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* BARRA DE BÚSQUEDA Y BOTÓN UNIFICADOS */
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

    /* BOTONES DE SUGERENCIAS DE CANCIONES */
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
        margin-bottom: 6px;
    }
    
    div.stButton > button:hover { 
        background-color: #ff2222 !important; 
        border-color: #ff2222 !important; 
        color: #ffffff !important; 
        transform: translateY(-1px);
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
    st.session_state.vinyl_color = "#e60000"

if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

def obtener_color_artista(artista):
    if not artista: return "#e60000"
    hash_object = hashlib.md5(artista.encode())
    return '#' + hash_object.hexdigest()[:6]

# Componente iframe de Reproducción
reproductor_html = ""
clase_animacion = ""

if st.session_state.video_id:
    clase_animacion = "spin"
    reproductor_html = f"""
    <iframe class="yt-player" width="280" height="75" 
        src="https://www.youtube.com/embed/{st.session_state.video_id}?autoplay=1&enablejsapi=1" 
        frameborder="0" allow="autoplay; encrypted-media" allowfullscreen>
    </iframe>
    <p style='color: #dddddd; font-family: "Inter", sans-serif; text-align: center; margin-top: 12px; font-size: 0.95rem; font-weight: 600;'>
        ▶ Reproduciendo: {st.session_state.song_title} — {st.session_state.artist_name}
    </p>
    """

# Componente HTML del Vinilo Animado
html_vinilo = f"""
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
        padding: 0;
    }}
    .vinyl {{
        width: 185px; height: 185px; border-radius: 50%; position: relative; 
        display: flex; justify-content: center; align-items: center;
        background: radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
                    repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
                    conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
        box-shadow: 0 8px 22px rgba(0,0,0,0.9), inset 0 0 1px rgba(255,255,255,0.2);
        border: 1px solid #1a1a1a;
    }}
    .center-label {{
        width: 66px; height: 66px; border-radius: 50%;
        background-color: {st.session_state.vinyl_color}; 
        display: flex; justify-content: center; align-items: center; z-index: 2;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.8);
        transition: background-color 0.6s ease;
    }}
    .center-hole {{ 
        width: 8px; height: 8px; background: #ffffff; border-radius: 50%; box-shadow: inset 0 0 2px rgba(0,0,0,0.8);
    }}
    .spin {{ animation: spin 2.2s linear infinite; }}
    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
    .yt-player {{ margin-top: 14px; border-radius: 12px; box-shadow: 0 0 12px {st.session_state.vinyl_color}; }}
</style>
</head>
<body>
    <div class="vinyl {clase_animacion}"><div class="center-label"><div class="center-hole"></div></div></div>
    {reproductor_html}
</body>
</html>
"""

altura_componente = 340 if st.session_state.video_id else 200
components.html(html_vinilo, height=altura_componente)

# ---------------------------------------------------------
# FORMULARIO DE BÚSQUEDA
# ---------------------------------------------------------
with st.form(key="search_form", border=False):
    col_btn, col_input = st.columns([0.18, 0.82], vertical_alignment="center")
    with col_btn:
        btn_buscar = st.form_submit_button("Buscar", use_container_width=True)
    with col_input:
        query_input = st.text_input("Búsqueda", placeholder="Buscar canción, artista o género...", label_visibility="collapsed")

# Al hacer submit en el formulario se actualiza la búsqueda actual
if btn_buscar and query_input.strip():
    st.session_state.current_query = query_input.strip()

# ---------------------------------------------------------
# RENDERIZADO DE SUGERENCIAS Y REPRODUCCIÓN
# ---------------------------------------------------------
if st.session_state.current_query:
    st.write(f"### Sugerencias")
    
    if ytmusic is None:
        st.error("Error al conectar con YouTube Music. Verifica que `ytmusicapi` esté instalado.")
    else:
        try:
            resultados = ytmusic.search(st.session_state.current_query, filter="songs", limit=8)
            
            if not resultados:
                st.info("No se encontraron resultados para tu búsqueda.")
            else:
                for idx, song in enumerate(resultados):
                    v_id = song.get('videoId')
                    if not v_id:
                        continue
                    
                    titulo = song.get('title', 'Canción desconocida')
                    artistas_list = song.get('artists', [])
                    artistas = ", ".join([a['name'] for a in artistas_list if 'name' in a]) or "Artista desconocido"
                    duracion = song.get('duration', '')
                    
                    texto_opcion = f"🎵  {titulo} — {artistas}" + (f" ({duracion})" if duracion else "")
                    
                    # Al hacer clic en una sugerencia, se actualiza la canción y se vuelve a renderizar
                    if st.button(texto_opcion, key=f"song_{v_id}_{idx}"):
                        st.session_state.video_id = v_id
                        st.session_state.song_title = titulo
                        st.session_state.artist_name = artistas
                        st.session_state.vinyl_color = obtener_color_artista(artistas)
                        st.rerun()
                        
        except Exception as e:
            st.error(f"Error al obtener sugerencias: {str(e)}")
