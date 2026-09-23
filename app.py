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

# CSS Global con tipografía Inter, Ola RGBIC y Buscador Unificado con Lupa Integrada
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

    /* OCULTAR COMPLETAMENTE 'Press Enter to apply' Y TEXTOS DE INSTRUCCIÓN */
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

    /* DISEÑO DE LA BARRA DE BÚSQUEDA EN CÁPSULA */
    div[data-testid="stTextInput"] > div > div {
        background-color: #16161a !important;
        border-radius: 50px !important; /* Cápsula redondeada */
        border: 2px solid #ff2222 !important;
        box-shadow: 0 0 15px rgba(255, 34, 34, 0.2) !important;
        transition: all 0.3s ease !important;
        height: 52px !important;
    }

    div[data-testid="stTextInput"] > div > div:focus-within {
        border-color: #ff5555 !important;
        box-shadow: 0 0 20px rgba(255, 34, 34, 0.45) !important;
    }

    div[data-testid="stTextInput"] input {
        background-color: transparent !important;
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        padding: 12px 55px 12px 22px !important; /* Espacio reservado para la lupa a la derecha */
        height: 48px !important;
    }

    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
    }

    /* POSICIONAR EL BOTÓN DE BÚSQUEDA EXACTAMENTE DENTRO DE LA PUNTA DERECHA DE LA BARRA */
    div[data-testid="element-container"]:has(div[data-testid="stTextInput"]) + div[data-testid="element-container"] {
        margin-top: -46px !important;
        margin-bottom: 22px !important;
        display: flex !important;
        justify-content: flex-end !important;
        padding-right: 6px !important;
        position: relative !important;
        z-index: 100 !important;
    }

    /* ESTILO DEL BOTÓN CON ÍCONO VECTORIAL DE LUPA BLANCA Y FONDO ROJO OPACO */
    div[data-testid="element-container"]:has(div[data-testid="stTextInput"]) + div[data-testid="element-container"] button {
        background-color: #821c1c !important; /* Rojo opaco */
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23ffffff' stroke-width='2.5'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' /%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: 18px 18px !important;
        color: transparent !important; /* Ocultar texto */
        border-radius: 50% !important; /* Botón circular */
        width: 40px !important;
        height: 40px !important;
        min-width: 40px !important;
        border: 1px solid #a82424 !important;
        cursor: pointer !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
        padding: 0 !important;
    }

    div[data-testid="element-container"]:has(div[data-testid="stTextInput"]) + div[data-testid="element-container"] button:hover {
        background-color: #a82424 !important;
        border-color: #ff2222 !important;
        box-shadow: 0 0 12px rgba(255, 34, 34, 0.5) !important;
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

# BARRA DE BÚSQUEDA INTEGRADA
query_input = st.text_input("", placeholder="Buscar canción, artista o género...", label_visibility="collapsed")
btn_buscar = st.button("", key="btn_buscar_lupa")

# Actualizar término de búsqueda al hacer clic en la lupa o presionar Enter
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
