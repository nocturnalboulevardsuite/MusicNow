import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic
import hashlib

# Inicializar buscador de YouTube Music
@st.cache_resource
def get_ytmusic():
    return YTMusic()

ytmusic = get_ytmusic()

# Configuración de la página (sin emoji en el icono)
st.set_page_config(page_title="MusicNow", layout="centered")

# CSS Global con fuentes góticas retro y buscador estilo burbuja
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=MedievalSharp&family=Pirata+One&display=swap');

    .stApp { 
        background-color: #0e0e10; 
        color: #e0e0e0; 
    }
    
    /* Fuente retro gótica para títulos */
    .gothic-title {
        font-family: 'Pirata One', cursive;
        color: #ff2222;
        text-align: center;
        font-size: 5.2rem;
        font-weight: 400;
        margin-bottom: -10px;
        letter-spacing: 3px;
        text-shadow: 0 0 15px rgba(255, 34, 34, 0.4);
    }
    
    .gothic-sub {
        font-family: 'MedievalSharp', cursive;
        color: #888888;
        text-align: center;
        font-size: 1.1rem;
        letter-spacing: 2px;
        margin-top: 0;
        margin-bottom: 15px;
        text-transform: uppercase;
    }

    /* Contenedor del buscador "Burbujeante" (Esquinas redondeadas y amplio espacio) */
    .stTextInput > div > div {
        background-color: #1a1a1e !important;
        border-radius: 18px !important;
        border: 2px solid #ff2222 !important;
        padding: 6px 12px !important;
        box-shadow: 0 4px 20px rgba(255, 34, 34, 0.15) !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div:focus-within {
        border-color: #ff5555 !important;
        box-shadow: 0 0 18px rgba(255, 34, 34, 0.4) !important;
    }

    /* Input interno (Amplio, sin estar aplastado) */
    .stTextInput input {
        background-color: transparent !important;
        color: #f0f0f0 !important;
        font-family: 'MedievalSharp', cursive, sans-serif !important;
        font-size: 1.15rem !important;
        padding: 12px 10px !important;
        height: auto !important;
    }

    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
    }

    /* Botones de sugerencias con tipografía retro */
    .stButton>button {
        background-color: #16161a; 
        color: #dcdcdc; 
        font-family: 'MedievalSharp', cursive, sans-serif;
        font-size: 1.05rem;
        border: 1px solid #2a2a30; 
        border-radius: 12px; 
        width: 100%; 
        text-align: left; 
        transition: all 0.2s ease;
        padding: 12px 18px;
        margin-bottom: 6px;
    }
    
    .stButton>button:hover { 
        background-color: #ff2222; 
        border-color: #ff2222; 
        color: #ffffff; 
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 34, 34, 0.3);
    }

    h3 {
        font-family: 'MedievalSharp', cursive !important;
        color: #cccccc !important;
        font-size: 1.3rem !important;
        margin-top: 20px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal gótico
st.markdown("<h1 class='gothic-title'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown("<p class='gothic-sub'>La rocola de la fiesta</p>", unsafe_allow_html=True)

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

# Reproductor de audio embebido
reproductor_html = ""
clase_animacion = ""

if st.session_state.video_id:
    clase_animacion = "spin"
    reproductor_html = f"""
    <iframe class="yt-player" width="280" height="75" 
        src="https://www.youtube.com/embed/{st.session_state.video_id}?autoplay=1&color=red" 
        frameborder="0" allow="autoplay; encrypted-media">
    </iframe>
    <p style='color: #dddddd; font-family: "MedievalSharp", cursive; text-align: center; margin-top: 14px; font-size: 1.1rem;'>
        Reproduciendo: {st.session_state.song_title}
    </p>
    """

# HTML / CSS del Vinilo Realista
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
        padding: 5px 0;
    }}
    
    .vinyl {{
        width: 190px; 
        height: 190px; 
        border-radius: 50%;
        position: relative; 
        display: flex; 
        justify-content: center; 
        align-items: center;
        
        background: 
            radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
            repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
            conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
            
        box-shadow: 0 10px 25px rgba(0,0,0,0.95), inset 0 0 1px rgba(255,255,255,0.25);
        border: 1px solid #1a1a1a;
    }}
    
    .center-label {{
        width: 68px; 
        height: 68px; 
        border-radius: 50%;
        background-color: {st.session_state.vinyl_color}; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        z-index: 2;
        box-shadow: inset 0 0 12px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.8);
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
        margin-top: 16px;
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

# Renderizar el vinilo
altura_componente = 360 if st.session_state.video_id else 220
components.html(html_vinilo, height=altura_componente)

# Buscador estilo burbuja abajo del vinilo (sin emojis)
query = st.text_input("", placeholder="Buscar cancion, artista o genero...")

# Lógica de búsqueda y resultados
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
