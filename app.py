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

    /* Ocultar instrucciones predeterminadas de Streamlit */
    div[data-testid="InputInstructions"], 
    div[data-testid="stInputInstructions"],
    [data-testid="stInputInstructions"],
    [data-testid="InputInstructions"],
    .stTextInputInstructions,
    div[data-testid="stTextInput"] small {
        display: none !important;
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

# Configuración del vinilo y reproductor interactivo
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
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    body {{
        background-color: transparent; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        margin: 0; 
        padding: 20px 0; /* Agrega espacio para que la sombra no se corte */
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: #ffffff;
    }}
    .vinyl {{
        width: 185px; height: 185px; border-radius: 50%; position: relative; 
        display: flex; justify-content: center; align-items: center;
        background: radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
                    repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
                    conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
        box-shadow: 0 8px 22px rgba(0,0,0,0.9), 0 0 20px {v_color};
        border: 1px solid #1a1a1a;
        cursor: pointer;
        margin-bottom: 5px;
    }}
    .center-label {{
        width: 76px; height: 76px; border-radius: 50%;
        display: flex; justify-content: center; align-items: center; z-index: 2;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 0 8px {v_color};
        transition: all 0.5s ease;
        {label_style}
    }}
    .center-hole {{ 
        width: 10px; height: 10px; background: #ffffff; border-radius: 50%; box-shadow: inset 0 0 2px rgba(0,0,0,0.8);
    }}
    .spin {{ animation: spin 2.2s linear infinite; }}
    .paused {{ animation-play-state: paused !important; }}
    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}

    /* TARJETA DEL REPRODUCTOR */
    .player-card {{
        width: 100%;
        max-width: 440px;
        background-color: #16161a;
        border: 1px solid #2a2a30;
        border-radius: 16px;
        padding: 16px 20px;
        margin-top: 18px;
        box-shadow: 0 0 20px rgba(0,0,0,0.6), 0 0 10px {v_color}40;
        box-sizing: border-box;
    }}
    .song-details {{
        text-align: center;
        margin-bottom: 12px;
        font-size: 0.92rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #f0f0f0;
    }}
    
    /* BARRA DE PROGRESO Y TIEMPO */
    .progress-container {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }}
    .time-stamp {{
        font-size: 0.78rem;
        color: #a0a0a0;
        min-width: 36px;
        font-weight: 500;
    }}
    .progress-bar {{
        flex-grow: 1;
        -webkit-appearance: none;
        appearance: none;
        height: 5px;
        border-radius: 5px;
        background: linear-gradient(to right, {v_color} 0%, #33333d 0%);
        outline: none;
        cursor: pointer;
    }}
    .progress-bar::-webkit-slider-thumb {{
        -webkit-appearance: none;
        appearance: none;
        width: 13px;
        height: 13px;
        border-radius: 50%;
        background: {v_color};
        cursor: pointer;
        box-shadow: 0 0 8px {v_color};
    }}

    /* CONTROLES (PLAY/PAUSA Y VOLUMEN) */
    .controls-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    .btn-play {{
        background-color: {v_color};
        color: #ffffff;
        border: none;
        border-radius: 50px;
        padding: 8px 22px;
        font-size: 0.9rem;
        font-weight: 700;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 0 10px {v_color}80;
    }}
    .btn-play:hover {{
        transform: scale(1.04);
    }}
    .volume-box {{
        display: flex;
        align-items: center;
        gap: 8px;
        color: #a0a0a0;
        font-size: 0.85rem;
    }}
    .volume-slider {{
        -webkit-appearance: none;
        appearance: none;
        width: 90px;
        height: 5px;
        border-radius: 5px;
        background: linear-gradient(to right, {v_color} 100%, #33333d 100%);
        outline: none;
        cursor: pointer;
    }}
    .volume-slider::-webkit-slider-thumb {{
        -webkit-appearance: none;
        appearance: none;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #ffffff;
        box-shadow: 0 0 6px {v_color};
        cursor: pointer;
    }}

    /* SOLUCIÓN AL BLOQUEO DE YOUTUBE: Tamaño normal pero totalmente transparente */
    .offscreen-player {{
        position: absolute;
        width: 200px;
        height: 200px;
        opacity: 0.001; 
        pointer-events: none;
        z-index: -99;
    }}

    .error-notice {{
        display: none;
        color: #ff4444;
        font-size: 0.82rem;
        text-align: center;
        margin-top: 8px;
    }}
</style>
</head>
<body>

    <!-- Vinilo Animado -->
    <div id="vinyl-disk" class="vinyl" onclick="togglePlay()">
        <div class="center-label"><div class="center-hole"></div></div>
    </div>

    <!-- Contenedor del Iframe API de Youtube -->
    <div class="offscreen-player">
        <div id="yt-player"></div>
    </div>

    <!-- Tarjeta Interactiva del Reproductor -->
    {"<div class='player-card'>" if v_id else "<div style='margin-top:15px; color:#777; font-size:0.9rem;'>Selecciona una canción para reproducir</div>"}
    {"<div class='song-details'>▶ " + s_title + " — " + s_artist + "</div>" if v_id else ""}
    {"<div class='progress-container'><span id='curr-time' class='time-stamp'>0:00</span><input type='range' id='progress' class='progress-bar' value='0' min='0' max='100' oninput='seekToTime(this.value)'><span id='total-dur' class='time-stamp'>0:00</span></div>" if v_id else ""}
    {"<div class='controls-row'><button id='play-btn' class='btn-play' onclick='togglePlay()'><i id='play-icon' class='fas fa-play'></i> <span id='btn-text'>Play</span></button><div class='volume-box'><i class='fas fa-volume-up'></i><input type='range' id='vol-slider' class='volume-slider' min='0' max='100' value='100' oninput='changeVolume(this.value)'></div></div>" if v_id else ""}
    {"<div id='err-msg' class='error-notice'>⚠️ Esta pista no permite reproducción incrustada. Elige otra canción.</div>" if v_id else ""}
    {"</div>" if v_id else ""}

    <script src="https://www.youtube.com/iframe_api"></script>
    <script>
        var player;
        var videoId = "{v_id}";
        var vColor = "{v_color}";
        var updateInterval;

        function onYouTubeIframeAPIReady() {{
            if (!videoId) return;
            player = new YT.Player('yt-player', {{
                height: '200', // Tamaño normal para evitar bloqueo por spam de YouTube
                width: '200',
                videoId: videoId,
                playerVars: {{
                    'autoplay': 0, 
                    'controls': 0,
                    'disablekb': 1,
                    'fs': 0,
                    'rel': 0,
                    'playsinline': 1,
                    'enablejsapi': 1
                }},
                events: {{
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange,
                    'onError': onPlayerError
                }}
            }});
        }}

        function onPlayerReady(event) {{
            // Intentar reproducir si el navegador lo permite
            try {{
                event.target.playVideo();
            }} catch (e) {{
                console.log("Esperando interacción del usuario.");
            }}
            startUpdateLoop();
        }}

        function updateUIState(playing) {{
            var vinyl = document.getElementById('vinyl-disk');
            var btnIcon = document.getElementById('play-icon');
            var btnText = document.getElementById('btn-text');

            if (playing) {{
                if (vinyl) {{ vinyl.classList.add('spin'); vinyl.classList.remove('paused'); }}
                if (btnIcon) btnIcon.className = "fas fa-pause";
                if (btnText) btnText.innerText = "Pausa";
            }} else {{
                if (vinyl) {{ vinyl.classList.add('paused'); }}
                if (btnIcon) btnIcon.className = "fas fa-play";
                if (btnText) btnText.innerText = "Play";
            }}
        }}

        function onPlayerStateChange(event) {{
            // YT.PlayerState.PLAYING == 1
            if (event.data === 1) {{
                updateUIState(true);
            }} 
            // Pausado (2), Terminado (0), Unstarted (-1), Cued (5)
            else if (event.data === 2 || event.data === 0 || event.data === -1 || event.data === 5) {{
                updateUIState(false);
            }}
        }}

        function togglePlay() {{
            if (!player || typeof player.getPlayerState !== 'function') return;
            var state = player.getPlayerState();
            
            if (state === 1 || state === 3) {{ // 1: Playing, 3: Buffering
                player.pauseVideo();
            }} else {{
                player.playVideo();
            }}
        }}

        function changeVolume(val) {{
            if (player && typeof player.setVolume === 'function') {{
                player.setVolume(val);
            }}
            var volSlider = document.getElementById('vol-slider');
            if (volSlider) {{
                volSlider.style.background = 'linear-gradient(to right, ' + vColor + ' ' + val + '%, #33333d ' + val + '%)';
            }}
        }}

        function seekToTime(val) {{
            if (player && typeof player.getDuration === 'function') {{
                var dur = player.getDuration();
                if (dur > 0) {{
                    var target = (val / 100) * dur;
                    player.seekTo(target, true);
                    var prog = document.getElementById('progress');
                    if (prog) {{
                        prog.style.background = 'linear-gradient(to right, ' + vColor + ' ' + val + '%, #33333d ' + val + '%)';
                    }}
                }}
            }}
        }}

        function formatTime(sec) {{
            sec = Math.floor(sec || 0);
            var m = Math.floor(sec / 60);
            var s = sec % 60;
            return m + ":" + (s < 10 ? "0" : "") + s;
        }}

        function startUpdateLoop() {{
            if (updateInterval) clearInterval(updateInterval);
            updateInterval = setInterval(function() {{
                if (player && typeof player.getCurrentTime === 'function' && typeof player.getDuration === 'function') {{
                    var cur = player.getCurrentTime();
                    var dur = player.getDuration();
                    if (dur > 0) {{
                        var pct = (cur / dur) * 100;
                        var currElem = document.getElementById('curr-time');
                        var totalElem = document.getElementById('total-dur');
                        var progElem = document.getElementById('progress');

                        if (currElem) currElem.innerText = formatTime(cur);
                        if (totalElem) totalElem.innerText = formatTime(dur);
                        if (progElem) {{
                            progElem.value = pct;
                            progElem.style.background = 'linear-gradient(to right, ' + vColor + ' ' + pct + '%, #33333d ' + pct + '%)';
                        }}
                    }}
                }}
            }}, 300);
        }}

        function onPlayerError(e) {{
            var err = document.getElementById('err-msg');
            if (err) err.style.display = 'block';
        }}
    </script>
</body>
</html>
"""

# AUMENTADO A 460px PARA QUE EL VINILO NUNCA SE VEA CORTADO
altura_componente = 460 if st.session_state.video_id else 210
components.html(html_reproductor_completo, height=altura_componente)

# ---------------------------------------------------------
# FORMULARIO DE BÚSQUEDA EN TIEMPO REAL
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
# BÚSQUEDA GLOBAL Y RESULTADOS CON MINIATURAS
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
                    
                    # Obtener miniatura devuelta por la API
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
