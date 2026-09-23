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

# CSS Global para modo oscuro y botones
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: white; }
    .stTextInput > div > div > input {
        background-color: #2b2b2b; color: white; border-radius: 20px; border: 2px solid #ff3333;
        padding: 10px 15px;
    }
    .stButton>button {
        background-color: #2b2b2b; color: white; border: 1px solid #ff3333; border-radius: 10px; width: 100%; text-align: left; transition: 0.3s;
        margin-bottom: 5px;
    }
    .stButton>button:hover { background-color: #ff3333; border-color: #ff3333; color: white; }
    </style>
""", unsafe_allow_html=True)

# Títulos
st.markdown("<h1 style='text-align: center; color: #ff3333; font-size: 4.5rem; font-weight: 900; margin-bottom: 0;'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; font-size: 1.2rem; margin-top: 0;'>La rocola de la fiesta</p>", unsafe_allow_html=True)

# Variables de estado de la canción
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
    st.session_state.song_title = None
    st.session_state.artist_name = None
    st.session_state.vinyl_color = "#ff3333" # Rojo por defecto como pediste

# Función para generar un color único dependiendo del artista
def obtener_color_artista(artista):
    if not artista: return "#ff3333"
    # Convierte el nombre del artista en un código de color Hexadecimal
    hash_object = hashlib.md5(artista.encode())
    return '#' + hash_object.hexdigest()[:6]

# --- EL VINILO (SIEMPRE VISIBLE EN EL MEDIO) ---
# Si hay canción reproduciendo, el vinilo gira
clase_animacion = "spin" if st.session_state.video_id else ""

# Si hay canción, preparamos el reproductor de YouTube
reproductor_html = ""
if st.session_state.video_id:
    reproductor_html = f"""
    <iframe class="yt-player" width="300" height="80" 
        src="https://www.youtube.com/embed/{st.session_state.video_id}?autoplay=1&color=red" 
        frameborder="0" allow="autoplay; encrypted-media">
    </iframe>
    <h3 style='color: white; font-family: sans-serif; text-align: center; margin-top: 15px;'>🎶 Reproduciendo: {st.session_state.song_title}</h3>
    """

# Código HTML/CSS del vinilo
html_vinilo = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{
        background-color: transparent; display: flex; flex-direction: column; 
        align-items: center; justify-content: center; margin: 0; padding: 20px 0;
    }}
    .vinyl {{
        width: 280px; height: 280px; background: #111; border-radius: 50%;
        position: relative; display: flex; justify-content: center; align-items: center;
        box-shadow: 0 0 30px rgba(0,0,0,0.9); border: 4px solid #1a1a1a;
    }}
    /* Surcos del vinilo */
    .vinyl::before {{ content: ''; position: absolute; width: 250px; height: 250px; border-radius: 50%; border: 1px solid #2a2a2a; }}
    .vinyl::after {{ content: ''; position: absolute; width: 210px; height: 210px; border-radius: 50%; border: 1px solid #2a2a2a; }}
    .vinyl-inner {{ content: ''; position: absolute; width: 170px; height: 170px; border-radius: 50%; border: 1px solid #2a2a2a; }}
    
    .center-label {{
        width: 90px; height: 90px; border-radius: 50%;
        background-color: {st.session_state.vinyl_color}; 
        display: flex; justify-content: center; align-items: center; z-index: 2;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
        border: 2px solid #222;
        transition: background-color 0.8s ease; /* Transición suave de color */
    }}
    .center-hole {{ width: 15px; height: 15px; background: #121212; border-radius: 50%; }}
    .spin {{ animation: spin 2s linear infinite; }}
    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
    
    .yt-player {{
        margin-top: 30px;
        border-radius: 10px;
        box-shadow: 0 0 15px {st.session_state.vinyl_color};
    }}
</style>
</head>
<body>
    <div class="vinyl {clase_animacion}">
        <div class="vinyl-inner"></div>
        <div class="center-label">
            <div class="center-hole"></div>
        </div>
    </div>
    {reproductor_html}
</body>
</html>
"""

# Renderizamos el vinilo en Streamlit (ajustamos el alto si está el reproductor activo)
altura_componente = 480 if st.session_state.video_id else 320
components.html(html_vinilo, height=altura_componente)

# --- BUSCADOR (ABAJO DEL VINILO) ---
query = st.text_input("🔍", placeholder="Ej: Gasolina Daddy Yankee...")

# Lógica de búsqueda
if query:
    st.write("### 🔥 Sugerencias:")
    try:
        # Buscar en YouTube Music (Filtro por canciones, trae 10 resultados)
        resultados = ytmusic.search(query, filter="songs", limit=10)
        
        for song in resultados:
            titulo = song.get('title', 'Desconocido')
            artistas = ", ".join([a['name'] for a in song.get('artists', [])])
            texto_boton = f"🎵 {titulo} - {artistas}"
            video_id = song.get('videoId')
            
            # Al hacer clic en un botón
            if video_id and st.button(texto_boton, key=video_id):
                st.session_state.video_id = video_id
                st.session_state.song_title = titulo
                st.session_state.artist_name = artistas
                # Cambiar el color basado en el nombre del artista
                st.session_state.vinyl_color = obtener_color_artista(artistas)
                st.rerun() # Recarga la app para que empiece a girar
    except Exception as e:
        st.error("Hubo un error al buscar la canción. Intenta buscar de otra manera.")
