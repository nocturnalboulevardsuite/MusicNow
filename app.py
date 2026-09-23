import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic
import random

# Inicializar buscador de YouTube Music
@st.cache_resource
def get_ytmusic():
    return YTMusic()

ytmusic = get_ytmusic()

# Configuración de la página
st.set_page_config(page_title="MusicNow", page_icon="🎵", layout="centered")

# CSS para forzar el fondo oscuro y detalles rojos
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: white; }
    .stTextInput > div > div > input {
        background-color: #2b2b2b; color: white; border-radius: 20px; border: 2px solid #ff3333;
    }
    .stButton>button {
        background-color: #2b2b2b; color: white; border: 1px solid #ff3333; border-radius: 10px; width: 100%; text-align: left; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #ff3333; border-color: #ff3333; color: white; }
    </style>
""", unsafe_allow_html=True)

# Título de la App
st.markdown("<h1 style='text-align: center; color: #ff3333; font-size: 4rem; font-weight: 900; margin-bottom: 0;'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; font-size: 1.2rem; margin-top: 0;'>La rocola de la fiesta</p>", unsafe_allow_html=True)

# Buscador de canciones
query = st.text_input("🔍", placeholder="/sugerencia (Ej: Gasolina Daddy Yankee)")

# Estado de la canción
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
    st.session_state.song_title = None
    st.session_state.vinyl_color = "#ff3333"

# Lógica de búsqueda real
if query:
    st.write("### 🔥 Resultados:")
    try:
        # Buscar en YouTube Music (Filtro por canciones)
        resultados = ytmusic.search(query, filter="songs", limit=10)
        
        for song in resultados:
            titulo = song.get('title', 'Desconocido')
            artistas = ", ".join([a['name'] for a in song.get('artists', [])])
            texto_boton = f"🎵 {titulo} - {artistas}"
            video_id = song.get('videoId')
            
            if video_id and st.button(texto_boton, key=video_id):
                st.session_state.video_id = video_id
                st.session_state.song_title = titulo
                colores = ["#ff3333", "#00ffcc", "#ff00ff", "#ffff00", "#0066ff", "#ff6600"]
                st.session_state.vinyl_color = random.choice(colores)
                st.rerun()
    except Exception as e:
        st.error("Hubo un error al buscar la canción. Intenta de nuevo.")

# Reproductor y Vinilo Animado
if st.session_state.video_id:
    st.markdown(f"<h3 style='text-align:center; color: white; margin-top: 20px;'>🎶 Reproduciendo: {st.session_state.song_title}</h3>", unsafe_allow_html=True)
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            background-color: transparent; display: flex; flex-direction: column; 
            align-items: center; justify-content: center; margin: 0; padding: 20px;
        }}
        .vinyl {{
            width: 250px; height: 250px; background: #111; border-radius: 50%;
            position: relative; display: flex; justify-content: center; align-items: center;
            box-shadow: 0 0 20px rgba(0,0,0,1); border: 4px solid #222;
        }}
        .vinyl::before {{ content: ''; position: absolute; width: 230px; height: 230px; border-radius: 50%; border: 1px solid #2a2a2a; }}
        .vinyl::after {{ content: ''; position: absolute; width: 190px; height: 190px; border-radius: 50%; border: 1px solid #2a2a2a; }}
        .center-label {{
            width: 80px; height: 80px; border-radius: 50%;
            background-color: {st.session_state.vinyl_color}; 
            display: flex; justify-content: center; align-items: center; z-index: 2;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
            border: 2px solid #222;
        }}
        .center-hole {{ width: 15px; height: 15px; background: #121212; border-radius: 50%; }}
        .spin {{ animation: spin 2s linear infinite; }}
        @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
        
        /* Ocultamos el video de YouTube pero dejamos el audio */
        .yt-player {{
            margin-top: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px {st.session_state.vinyl_color};
        }}
    </style>
    </head>
    <body>
        <div class="vinyl spin">
            <div class="center-label">
                <div class="center-hole"></div>
            </div>
        </div>
        
        <!-- Reproductor de YouTube embebido -->
        <iframe class="yt-player" width="300" height="80" 
            src="https://www.youtube.com/embed/{st.session_state.video_id}?autoplay=1&color=red" 
            frameborder="0" allow="autoplay; encrypted-media">
        </iframe>
    </body>
    </html>
    """
    
    # Renderizar el HTML
    components.html(html_code, height=400)
