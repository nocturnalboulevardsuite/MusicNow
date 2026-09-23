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

# CSS Global con tipografía Inter, Ola RGBIC y Buscador Cápsula con Lupa Integrada
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');

    .stApp { 
        background-color: #0e0e10; 
        color: #ffffff; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Elevar todo el contenido hacia arriba */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 680px !important;
    }

    /* Título Minimalista */
    .minimal-title {
        font-family: 'Inter', sans-serif;
        color: #ff2222;
        text-align: center;
        font-size: 3.8rem;
        font-weight: 900;
        margin-bottom: 4px;
        letter-spacing: -1.5px;
    }
    
    /* Subtítulo: Letra roja base con una ola de luz RGBIC */
    .minimal-sub-wave {
        font-family: 'Inter', sans-serif;
        text-align: center;
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 22px;
        letter-spacing: -0.2px;
        
        background: linear-gradient(
            90deg, 
            #ff2222 0%, 
            #ff2222 20%, 
            #ff6b00 32%, 
            #00f0ff 42%, 
            #a855f7 52%, 
            #ec4899 62%, 
            #ff2222 75%, 
            #ff2222 100%
        );
        background-size: 260% 100%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: rgbWaveSweep 3.8s ease-in-out infinite alternate;
    }

    @keyframes rgbWaveSweep {
        0% { background-position: 100% 0%; }
        100% { background-position: 0% 0%; }
    }

    /* OCULTAR COMPLETAMENTE 'Press Enter to apply' Y CUALQUIER TEXTO DE INSTRUCCIÓN */
    div[data-testid="stInputInstructions"], 
    small[data-testid="stInputInstructions"],
    .stInputInstructions,
    [data-testid="stInputInstructions"] * {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        width: 0 !important;
    }

    /* CONTENEDOR EN CÁPSULA DEL BUSCADOR */
    .search-wrapper {
        position: relative !important;
        width: 100% !important;
        margin-top: 10px !important;
        margin-bottom: 20px !important;
    }

    .search-wrapper div[data-testid="stTextInput"] {
        width: 100% !important;
    }

    .search-wrapper input {
        background-color: #16161a !important;
        border-radius: 50px !important; /* Forma redondeada de cápsula perfecta */
        border: 2px solid #ff2222 !important;
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        padding: 12px 55px 12px 22px !important; /* Espacio a la derecha para la lupa */
        height: 52px !important;
        box-shadow: 0 0 15px rgba(255, 34, 34, 0.25) !important;
        transition: all 0.3s ease !important;
    }

    .search-wrapper input:focus {
        border-color: #ff5555 !important;
        box-shadow: 0 0 20px rgba(255, 34, 34, 0.45) !important;
        outline: none !important;
    }

    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
    }

    /* BOTÓN CIRCULAR CON LUPA EN LA PUNTA INTERIOR DERECHA */
    .search-btn-icon {
        position: absolute !important;
        right: 7px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        z-index: 10 !important;
    }

    .search-btn-icon .stButton > button {
        background-color: #7a1d1d !important; /* Rojo opaco */
        color: #ffffff !important;
        border-radius: 50% !important; /* Botón circular */
        width: 38px !important;
        height: 38px !important;
        min-width: 38px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: 1px solid #a82424 !important;
        font-size: 1.1rem !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        cursor: pointer !important;
    }

    .search-btn-icon .stButton > button:hover {
        background-color: #ff2222 !important;
        border-color: #ff5555 !important;
        box-shadow: 0 0 10px rgba(255, 34, 34, 0.5) !important;
        transform: scale(1.05) !important;
    }

    /* Botones de sugerencias de canciones */
    .stButton>button {
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
    
    .stButton>button:hover { 
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

# Estado global de reproducción
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
    st.session_state.song_title = None
    st.session_state.artist_name = None
    st.session_state.vinyl_color = "#e60000"

if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

# Generador de color por artista
def obtener_color_artista(artista):
    if not artista: return "#e60000"
    hash_object = hashlib.md5(artista.encode())
    return '#' + hash_object.hexdigest()[:6]

# Reproductor embebido
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
        width: 185px; 
        height: 185px; 
        border-radius: 50%;
        position: relative; 
        display: flex; 
        justify-content: center; 
        align-items: center;
        
        background: 
            radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
            repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
            conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
            
        box-shadow: 0 8px 22px rgba(0,0,0,0.9), inset 0 0 1px rgba(255,255,255,0.2);
        border: 1px solid #1a1a1a;
    }}
    
    .center-label {{
        width: 66px; 
        height: 66px; 
        border-radius: 50%;
        background-color: {st.session_state.vinyl_color}; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        z-index: 2;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.8);
        transition: background-color 0.6s ease;
    }}
    
    .center-hole {{ 
        width: 8px; 
        height: 8px; 
        background: #ffffff; 
        border-radius: 50%; 
        box-shadow: inset 0 0 2px rgba(0,0,0,0.8);
    }}
    
    .spin {{ 
        animation: spin 2.2s linear infinite; 
    }}
    
    @keyframes spin {{ 
        100% {{ transform: rotate(360deg); }} 
    }}
    
    .yt-player {{
        margin-top: 14px;
        border-radius: 12px;
        box-shadow: 0 0 12px {st.session_state.vinyl_color};
    }}
</style>
</head>
<body>
    <div class="vinyl {clase_animacion}">
        <div class="center-label">
            <div class="center-hole"></div>
        </div>
    </div>
    {reproductor_html}
</body>
</html>
"""

# Renderizar vinilo
altura_componente = 340 if st.session_state.video_id else 200
components.html(html_vinilo, height=altura_componente)

# BARRA DE BÚSQUEDA EN CÁPSULA CON LUPA INTEGRADA DENTRO
st.markdown('<div class="search-wrapper">', unsafe_allow_html=True)

query_input = st.text_input("", placeholder="Buscar canción, artista o género...", label_visibility="collapsed")

st.markdown('<div class="search-btn-icon">', unsafe_allow_html=True)
btn_buscar = st.button("🔍", key="btn_buscar_lupa")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Actualizar término de búsqueda al hacer clic en la Lupa o presionar Enter
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
