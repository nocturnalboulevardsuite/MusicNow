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
st.set_page_config(page_title="MusicNow", page_icon="🎵", layout="centered")

# CSS Global para interfaz oscura, buscador minimalista y botones
st.markdown("""
    <style>
    .stApp { 
        background-color: #121212; 
        color: white; 
    }
    
    /* Buscador minimalista redondeado con borde rojo */
    .stTextInput > div > div > input {
        background-color: #1a1a1a !important;
        color: white !important;
        border-radius: 30px !important;
        border: 2px solid #ff3333 !important;
        padding: 12px 22px !important;
        font-size: 1rem !important;
        box-shadow: none !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #ff1a1a !important;
        box-shadow: 0 0 12px rgba(255, 51, 51, 0.4) !important;
    }

    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
        border-radius: 30px !important;
    }

    /* Estilo de los botones de sugerencia */
    .stButton>button {
        background-color: #1e1e1e; 
        color: white; 
        border: 1px solid #333; 
        border-radius: 12px; 
        width: 100%; 
        text-align: left; 
        transition: all 0.2s ease;
        padding: 10px 15px;
        margin-bottom: 4px;
    }
    .stButton>button:hover { 
        background-color: #ff3333; 
        border-color: #ff3333; 
        color: white; 
        transform: translateY(-1px);
    }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.markdown("<h1 style='text-align: center; color: #ff3333; font-size: 3.8rem; font-weight: 900; margin-bottom: 0;'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #777; font-size: 1.1rem; margin-top: 0; margin-bottom: 10px;'>La rocola de la fiesta</p>", unsafe_allow_html=True)

# Estado global de reproducción
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
    st.session_state.song_title = None
    st.session_state.artist_name = None
    st.session_state.vinyl_color = "#e60000" # Rojo clásico de la foto

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
    <p style='color: #eee; font-family: sans-serif; text-align: center; margin-top: 12px; font-weight: bold;'>
        🎶 {st.session_state.song_title}
    </p>
    """

# HTML / CSS del Vinilo Realista (Efecto de luz diagonal, surcos y punto blanco al centro)
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
        padding: 10px 0;
    }}
    
    /* Disco de vinilo realista */
    .vinyl {{
        width: 200px; 
        height: 200px; 
        border-radius: 50%;
        position: relative; 
        display: flex; 
        justify-content: center; 
        align-items: center;
        
        /* Capas de textura: Surcos radiales + reflejo de luz cónico brillante */
        background: 
            radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
            repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
            conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
            
        box-shadow: 0 12px 28px rgba(0,0,0,0.95), inset 0 0 1px rgba(255,255,255,0.25);
        border: 1px solid #1a1a1a;
    }}
    
    /* Etiqueta central circular */
    .center-label {{
        width: 72px; 
        height: 72px; 
        border-radius: 50%;
        background-color: {st.session_state.vinyl_color}; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        z-index: 2;
        box-shadow: inset 0 0 12px rgba(0,0,0,0.5), 0 0 2px rgba(0,0,0,0.8);
        transition: background-color 0.6s ease;
    }}
    
    /* Orificio central blanco como el de la foto */
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
        margin-top: 18px;
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

# Renderizar el componente del vinilo
altura_componente = 370 if st.session_state.video_id else 240
components.html(html_vinilo, height=altura_componente)

# Buscador abajo del vinilo
query = st.text_input("", placeholder="Ej: Gasolina Daddy Yankee...")

# Lógica de búsqueda y resultados
if query:
    st.write("### 🔥 Sugerencias:")
    try:
        resultados = ytmusic.search(query, filter="songs", limit=10)
        
        for song in resultados:
            titulo = song.get('title', 'Desconocido')
            artistas = ", ".join([a['name'] for a in song.get('artists', [])])
            texto_boton = f"🎵 {titulo} - {artistas}"
            video_id = song.get('videoId')
            
            if video_id and st.button(texto_boton, key=video_id):
                st.session_state.video_id = video_id
                st.session_state.song_title = titulo
                st.session_state.artist_name = artistas
                st.session_state.vinyl_color = obtener_color_artista(artistas)
                st.rerun()
    except Exception as e:
        st.error("No se encontraron resultados. Intenta de nuevo.")
