import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic
import hashlib

# Inicializar buscador de YouTube Music
@st.cache_resource
def get_ytmusic():
    return YTMusic()

ytmusic = get_ytmusic()

# Configuración de la página
st.set_page_config(page_title="MusicNow", layout="centered")

# CSS Global corregido y a prueba de bugs
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

    /* 1. ELIMINAR TEXTO MOLESTO "Press Enter to apply" */
    div[data-testid="InputInstructions"], 
    div[data-testid="stTextInputInstructions"],
    .stTextInputInstructions,
    small {
        display: none !important;
        opacity: 0 !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        position: absolute !important;
    }

    /* 2. DISEÑO DE LA CÁPSULA (INPUT) */
    /* Eliminar el margen inferior para que el botón pueda subir exactamente */
    div[data-testid="element-container"]:has(.search-marker) + div[data-testid="element-container"] {
        margin-bottom: 0 !important;
    }

    div[data-testid="element-container"]:has(.search-marker) + div[data-testid="element-container"] div[data-baseweb="input"] {
        border-radius: 50px !important;
        border: 2px solid #ff2222 !important;
        background-color: #16161a !important;
        height: 56px !important;
        padding-right: 54px !important; /* Crucial: Evita que el texto escrito quede debajo del botón */
        box-shadow: 0 0 15px rgba(255, 34, 34, 0.2) !important;
    }

    div[data-testid="element-container"]:has(.search-marker) + div[data-testid="element-container"] div[data-baseweb="input"]:focus-within {
        border-color: #ff5555 !important;
        box-shadow: 0 0 20px rgba(255, 34, 34, 0.45) !important;
    }

    div[data-testid="element-container"]:has(.search-marker) + div[data-testid="element-container"] input {
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        padding-left: 20px !important;
        background-color: transparent !important;
    }

    /* 3. CONTENEDOR DEL BOTÓN SUPERPUESTO (ESTILO DIBUJO) */
    div[data-testid="element-container"]:has(.search-marker) + div + div {
        margin-top: -56px !important; /* Sube el contenedor la altura exacta del input */
        margin-bottom: 25px !important; 
        display: flex !important;
        justify-content: flex-end !important; /* Mueve el botón a la derecha */
        align-items: center !important; /* Lo centra verticalmente */
        height: 56px !important;
        padding-right: 8px !important; /* Lo separa ligeramente del borde derecho de la cápsula */
        pointer-events: none !important; /* Permite clics al input que está detrás */
        position: relative !important;
        z-index: 10 !important;
    }

    /* 4. EL BOTÓN CIRCULAR CON LUPA */
    div[data-testid="element-container"]:has(.search-marker) + div + div button {
        pointer-events: auto !important; /* Reactiva los clics solo para el botón */
        background-color: #cc0000 !important; /* Rojo opaco */
        border: none !important;
        border-radius: 50% !important; /* Forma 100% circular */
        width: 40px !important;
        height: 40px !important;
        min-width: 40px !important; 
        max-width: 40px !important;
        min-height: 40px !important;
        flex-shrink: 0 !important; /* FIX: Evita que el botón se aplaste y se vea como una línea vertical */
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="element-container"]:has(.search-marker) + div + div button:hover {
        background-color: #ff2222 !important;
        transform: scale(1.05) !important;
        box-shadow: 0 0 10px rgba(255, 34, 34, 0.6) !important;
    }

    /* Ocultar texto predeterminado e inyectar ícono SVG limpio */
    div[data-testid="element-container"]:has(.search-marker) + div + div button p {
        display: none !important;
    }
    div[data-testid="element-container"]:has(.search-marker) + div + div button::after {
        content: "";
        display: block;
        width: 18px;
        height: 18px;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23ffffff' stroke-width='3'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' /%3E%3C/svg%3E");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }

    /* Botones de sugerencias de canciones */
    .stButton>button:not(:has(p)) { /* Excluye la lupa de este estilo general */
        background-color: #16161a; 
        color: #e0e0e0; 
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        font-weight: 500;
        border: 1px solid #2a2a30; 
        border-radius: 12px; 
        width: 100%; 
        text-align: left; 
        transition: all 0.2s ease;
        padding: 10px 16px;
        margin-bottom: 5px;
    }
    
    .stButton>button:hover:not(:has(p)) { 
        background-color: #ff2222; 
        border-color: #ff2222; 
        color: #ffffff; 
        transform: translateY(-1px);
    }

    h3 {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-top: 15px !important;
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
    return '#' + hashlib.md5(artista.encode()).hexdigest()[:6]

# Reproductor
reproductor_html = ""
clase_animacion = ""

if st.session_state.video_id:
    clase_animacion = "spin"
    reproductor_html = f"""
    <iframe class="yt-player" width="280" height="75" 
        src="https://www.youtube.com/embed/{st.session_state.video_id}?autoplay=1&color=red" 
        frameborder="0" allow="autoplay; encrypted-media">
    </iframe>
    <p style='color: #dddddd; font-family: "Inter", sans-serif; text-align: center; margin-top: 12px; font-size: 0.95rem; font-weight: 600;'>
        Reproduciendo: {st.session_state.song_title}
    </p>
    """

# Componente HTML del Vinilo
html_vinilo = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ background-color: transparent; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0; padding: 0; }}
    .vinyl {{ width: 185px; height: 185px; border-radius: 50%; position: relative; display: flex; justify-content: center; align-items: center; background: radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%), repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px), conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg); box-shadow: 0 8px 22px rgba(0,0,0,0.9), inset 0 0 1px rgba(255,255,255,0.2); border: 1px solid #1a1a1a; }}
    .center-label {{ width: 66px; height: 66px; border-radius: 50%; background-color: {st.session_state.vinyl_color}; display: flex; justify-content: center; align-items: center; z-index: 2; box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.8); transition: background-color 0.6s ease; }}
    .center-hole {{ width: 8px; height: 8px; background: #ffffff; border-radius: 50%; box-shadow: inset 0 0 2px rgba(0,0,0,0.8); }}
    .spin {{ animation: spin 2.2s linear infinite; }}
    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
    .yt-player {{ margin-top: 14px; border-radius: 12px; box-shadow: 0 0 12px {st.session_state.vinyl_color}; }}
</style>
</head>
<body>
    <div class="vinyl {clase_animacion}">
        <div class="center-label"><div class="center-hole"></div></div>
    </div>
    {reproductor_html}
</body>
</html>
"""

altura_componente = 340 if st.session_state.video_id else 200
components.html(html_vinilo, height=altura_componente)

# ---------------------------------------------------------
# BARRA DE BÚSQUEDA INTEGRADA CON MARCADOR INVISIBLE
# ---------------------------------------------------------
st.markdown('<span class="search-marker" style="display:none;"></span>', unsafe_allow_html=True)
query_input = st.text_input("", placeholder="Buscar canción, artista o género...", label_visibility="collapsed")
btn_buscar = st.button("Buscar", key="btn_buscar_lupa")

if (btn_buscar or query_input) and query_input:
    st.session_state.current_query = query_input

# Resultados
if st.session_state.current_query:
    st.write("### Sugerencias")
    try:
        resultados = ytmusic.search(st.session_state.current_query, filter="songs", limit=10)
        
        for song in resultados:
            titulo = song.get('title', 'Desconocido')
            artistas = ", ".join([a['name'] for a in song.get('artists', [])])
            texto_boton = f"{titulo} - {artistas}"
            video_id = song.get('videoId')
            
            if video_id and st.button(texto_boton, key=video_id):
                st.session_state.video_id = video_id
                st.session_state.song_title = titulo
                st.session_state.artist_name = artistas
                st.session_state.vinyl_color = obtener_color_artista(artistas)
                st.rerun()
    except Exception as e:
        st.error("No se encontraron resultados. Intenta de nuevo.")
