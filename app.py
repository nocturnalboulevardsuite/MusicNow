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

# CSS Global con diseño elevado, tipografía Inter y efecto RGBIC
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');

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
        margin-bottom: 2px;
        letter-spacing: -1.5px;
    }
    
    /* Subtítulo en Rojo */
    .minimal-sub {
        font-family: 'Inter', sans-serif;
        color: #ff2222;
        text-align: center;
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 0;
        margin-bottom: 15px;
    }

    /* Texto con efecto RGBIC animado */
    .rgbic-text {
        background: linear-gradient(90deg, #ff0055, #ff5000, #00f0ff, #7000ff, #ff0055);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: rgbicAnimation 3s ease infinite;
        font-weight: 800;
    }

    @keyframes rgbicAnimation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Buscador minimalista redondeado */
    .stTextInput > div > div {
        background-color: #16161a !important;
        border-radius: 25px !important;
        border: 2px solid #ff2222 !important;
        padding: 2px 10px !important;
        box-shadow: 0 4px 15px rgba(255, 34, 34, 0.15) !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div:focus-within {
        border-color: #ff5555 !important;
        box-shadow: 0 0 15px rgba(255, 34, 34, 0.35) !important;
    }

    .stTextInput input {
        background-color: transparent !important;
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        padding: 10px 10px !important;
    }

    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
    }

    /* Botones de sugerencias minimalistas */
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
    "<p class='minimal-sub'>Busca la <span class='rgbic-text'>canción o música</span> que quieras y reprodúcela ahora mismo</p>", 
    unsafe_allow_html=True
)

# Estado global de reproducción
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
    st.session_state.song_title = None
    st.session_state.artist_name = None
    st.session_state.vinyl_color = "#e60000"

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

# Buscador minimalista
query = st.text_input("", placeholder="Buscar canción, artista o género...")

# Resultados
if query:
    st.write("### Sugerencias")
    try:
        resultados = ytmusic.search(query, filter="songs", limit=10)
        
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
