import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic
import random
import time
import urllib.parse

# Inicializar buscador de YouTube Music
@st.cache_resource
def get_ytmusic():
    try:
        return YTMusic()
    except Exception:
        return None

ytmusic = get_ytmusic()

# Configuración de la página en formato ancho (wide)
st.set_page_config(page_title="MusicNow - Party Mode", layout="wide")

# ---------------------------------------------------------
# SALA COMPARTIDA GLOBALMENTE ENTRE TODOS LOS DISPOSITIVOS
# ---------------------------------------------------------
class SharedPartyRoom:
    def __init__(self):
        self.playlist = []
        self.current_index = -1

@st.cache_resource
def get_party_room():
    return SharedPartyRoom()

room = get_party_room()

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
        padding-bottom: 2rem !important;
        max-width: 1200px !important;
    }

    .minimal-title {
        font-family: 'Inter', sans-serif;
        color: #ff2222;
        text-align: center;
        font-size: 3.5rem;
        font-weight: 900;
        margin-bottom: 2px;
        letter-spacing: -1.5px;
    }
    
    .minimal-sub-wave {
        font-family: 'Inter', sans-serif;
        text-align: center;
        font-size: 1rem;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 25px;
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

    /* BARRA DE BÚSQUEDA Y BOTÓN */
    div[data-testid="stForm"] {
        background-color: #16161a !important;
        border: 2px solid #ff2222 !important;
        border-radius: 14px !important;
        padding: 4px 8px !important;
        box-shadow: 0 0 12px rgba(255, 34, 34, 0.25) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        margin-top: 10px !important;
        margin-bottom: 15px !important;
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

    /* BOTONES GENERALES */
    div.stButton > button {
        background-color: #16161a; 
        color: #e0e0e0; 
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        font-weight: 500;
        border: 1px solid #2a2a30; 
        border-radius: 12px; 
        width: 100%; 
        transition: all 0.2s ease;
        padding: 8px 12px;
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
        margin-top: 5px !important;
        margin-bottom: 12px !important;
    }

    /* ESTILO DE LA LISTA DE ESPERA TIPO SPOTIFY ROJO TRANSPARENTE */
    div[data-testid="stColumn"]:nth-child(2) {
        background: rgba(255, 34, 34, 0.05) !important;
        border: 1px solid rgba(255, 34, 34, 0.25) !important;
        border-radius: 18px !important;
        padding: 18px 16px !important;
        box-shadow: 0 8px 32px rgba(255, 0, 0, 0.15), inset 0 0 15px rgba(255, 34, 34, 0.03) !important;
        backdrop-filter: blur(12px) !important;
    }

    /* Filas individuales de canciones en la playlist */
    div[data-testid="stColumn"]:nth-child(2) div[data-testid="stHorizontalBlock"] {
        background: rgba(22, 22, 26, 0.65) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        padding: 6px 10px !important;
        margin-bottom: 8px !important;
        transition: all 0.25s ease !important;
    }

    div[data-testid="stColumn"]:nth-child(2) div[data-testid="stHorizontalBlock"]:hover {
        background: rgba(255, 34, 34, 0.15) !important;
        border-color: rgba(255, 34, 34, 0.35) !important;
    }

    /* Ajuste de botones pequeños de la lista */
    div[data-testid="stColumn"]:nth-child(2) div.stButton > button {
        padding: 4px 6px !important;
        font-size: 0.8rem !important;
        border-radius: 8px !important;
        min-height: 36px !important;
        height: 36px !important;
    }

    /* CONTENEDOR DEL CÓDIGO QR */
    .qr-container {
        background: rgba(22, 22, 26, 0.8);
        border: 1px solid rgba(255, 34, 34, 0.3);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 0 25px rgba(255, 34, 34, 0.15);
        margin-top: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# Encabezado principal
st.markdown("<h1 class='minimal-title'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='minimal-sub-wave'>Busca una canción y añádelo a la lista</p>", 
    unsafe_allow_html=True
)

# Estado individual del usuario (búsqueda y cooldown por teléfono)
if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

if 'last_added_time' not in st.session_state:
    st.session_state.last_added_time = 0

COOLDOWN_SECONDS = 120  # 2 minutos de espera entre cada canción agregada

def obtener_color_aleatorio():
    colores = [
        "#ff2222", "#00f0ff", "#a855f7", "#ec4899", 
        "#ff9500", "#00ff88", "#3b82f6", "#ff206e", 
        "#10b981", "#e11d48", "#8b5cf6", "#f59e0b"
    ]
    return random.choice(colores)

def reproducir_indice(idx):
    if 0 <= idx < len(room.playlist):
        room.current_index = idx

def siguiente_cancion():
    if room.playlist and room.current_index < len(room.playlist) - 1:
        room.current_index += 1

def anterior_cancion():
    if room.playlist and room.current_index > 0:
        room.current_index -= 1

def agregar_a_playlist(song):
    room.playlist.append(song)
    if room.current_index == -1:
        room.current_index = 0

def eliminar_de_playlist(idx):
    if 0 <= idx < len(room.playlist):
        room.playlist.pop(idx)
        if len(room.playlist) == 0:
            room.current_index = -1
        elif room.current_index >= len(room.playlist):
            room.current_index = len(room.playlist) - 1

# Obtener canción actual
cancion_actual = None
if 0 <= room.current_index < len(room.playlist):
    cancion_actual = room.playlist[room.current_index]

v_id = cancion_actual['video_id'] if cancion_actual else ""
s_title = cancion_actual['title'] if cancion_actual else ""
s_artist = cancion_actual['artist'] if cancion_actual else ""
v_color = cancion_actual['color'] if cancion_actual else "#ff2222"
thumb_url = cancion_actual['thumbnail'] if cancion_actual else ""

label_style = f"background-image: url('{thumb_url}'); background-size: cover; background-position: center; border: 2px solid {v_color};" if thumb_url else f"background-color: {v_color};"

# ---------------------------------------------------------
# ESTRUCTURA EN 2 COLUMNAS (REPRODUCTOR + PLAYLIST)
# ---------------------------------------------------------
col_main, col_queue = st.columns([1.55, 1.05], gap="large")

with col_main:
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
            justify-content: flex-start; 
            margin: 0; 
            padding: 12px 10px;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            color: #ffffff;
            box-sizing: border-box;
        }}
        .vinyl {{
            width: 170px; height: 170px; border-radius: 50%; position: relative; 
            display: flex; justify-content: center; align-items: center;
            background: radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
                        repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
                        conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
            box-shadow: 0 6px 20px rgba(0,0,0,0.8), 0 0 18px {v_color};
            border: 1px solid #1a1a1a;
            cursor: pointer;
            margin-top: 4px;
            margin-bottom: 12px;
            flex-shrink: 0;
        }}
        .center-label {{
            width: 70px; height: 70px; border-radius: 50%;
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

        .player-card {{
            width: 100%;
            max-width: 440px;
            background-color: #16161a;
            border: 1px solid #2a2a30;
            border-radius: 16px;
            padding: 16px 20px;
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
        .btn-play:hover {{ transform: scale(1.04); }}
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

        .offscreen-player {{
            position: absolute;
            width: 200px;
            height: 200px;
            opacity: 0.001; 
            pointer-events: none;
            z-index: -99;
        }}
    </style>
    </head>
    <body>

        <div id="vinyl-disk" class="vinyl" onclick="togglePlay()">
            <div class="center-label"><div class="center-hole"></div></div>
        </div>

        <div class="offscreen-player"><div id="yt-player"></div></div>

        {"<div class='player-card'>" if v_id else "<div style='margin-top:10px; color:#777; font-size:0.9rem;'>Agrega una canción a la lista para comenzar</div>"}
        {"<div class='song-details'>▶ " + s_title + " — " + s_artist + "</div>" if v_id else ""}
        {"<div class='progress-container'><span id='curr-time' class='time-stamp'>0:00</span><input type='range' id='progress' class='progress-bar' value='0' min='0' max='100' oninput='seekToTime(this.value)'><span id='total-dur' class='time-stamp'>0:00</span></div>" if v_id else ""}
        {"<div class='controls-row'><button id='play-btn' class='btn-play' onclick='togglePlay()'><i id='play-icon' class='fas fa-play'></i> <span id='btn-text'>Play</span></button><div class='volume-box'><i class='fas fa-volume-up'></i><input type='range' id='vol-slider' class='volume-slider' min='0' max='100' value='100' oninput='changeVolume(this.value)'></div></div>" if v_id else ""}
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
                    height: '200',
                    width: '200',
                    videoId: videoId,
                    playerVars: {{
                        'autoplay': 1, 
                        'controls': 0,
                        'disablekb': 1,
                        'fs': 0,
                        'rel': 0,
                        'playsinline': 1,
                        'enablejsapi': 1
                    }},
                    events: {{
                        'onReady': onPlayerReady,
                        'onStateChange': onPlayerStateChange
                    }}
                }});
            }}

            function onPlayerReady(event) {{
                try {{ event.target.playVideo(); }} catch (e) {{}}
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
                if (event.data === 1) updateUIState(true);
                else if (event.data === 2 || event.data === 0 || event.data === -1 || event.data === 5) updateUIState(false);
            }}

            function togglePlay() {{
                if (!player || typeof player.getPlayerState !== 'function') return;
                var state = player.getPlayerState();
                if (state === 1 || state === 3) player.pauseVideo();
                else player.playVideo();
            }}

            function changeVolume(val) {{
                if (player && typeof player.setVolume === 'function') player.setVolume(val);
                var volSlider = document.getElementById('vol-slider');
                if (volSlider) volSlider.style.background = 'linear-gradient(to right, ' + vColor + ' ' + val + '%, #33333d ' + val + '%)';
            }}

            function seekToTime(val) {{
                if (player && typeof player.getDuration === 'function') {{
                    var dur = player.getDuration();
                    if (dur > 0) {{
                        player.seekTo((val / 100) * dur, true);
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
        </script>
    </body>
    </html>
    """

    altura_componente = 480 if cancion_actual else 240
    components.html(html_reproductor_completo, height=altura_componente)

    # FORMULARIO DE BÚSQUEDA
    with st.form(key="search_form", border=False):
        col_btn, col_input = st.columns([0.22, 0.78], vertical_alignment="center")
        with col_btn:
            btn_buscar = st.form_submit_button("Buscar", use_container_width=True)
        with col_input:
            query_input = st.text_input("Búsqueda", placeholder="Buscar canción, artista o género...", label_visibility="collapsed")

    if btn_buscar and query_input.strip():
        st.session_state.current_query = query_input.strip()

    # BOTONES SIGUIENTE Y ANTERIOR
    if room.playlist:
        col_prev, col_info, col_next = st.columns([0.35, 0.3, 0.35], vertical_alignment="center")
        with col_prev:
            st.button("⏮️ Anterior", on_click=anterior_cancion, disabled=(room.current_index <= 0), use_container_width=True)
        with col_info:
            st.markdown(f"<div style='text-align:center; font-size:0.85rem; color:#a0a0a0;'>{room.current_index + 1} de {len(room.playlist)}</div>", unsafe_allow_html=True)
        with col_next:
            st.button("Siguiente ⏭️", on_click=siguiente_cancion, disabled=(room.current_index >= len(room.playlist) - 1), use_container_width=True)

    # RESULTADOS DE BÚSQUEDA
    if st.session_state.current_query:
        st.write("### Sugerencias")
        if ytmusic is None:
            st.error("No se pudo conectar a YouTube Music.")
        else:
            try:
                resultados = ytmusic.search(st.session_state.current_query, filter="videos", limit=5)
                if not resultados:
                    resultados = ytmusic.search(st.session_state.current_query, limit=5)
                
                resultados = resultados[:5] if resultados else []
                
                if not resultados:
                    st.info("No se encontraron resultados para tu búsqueda.")
                else:
                    for idx, item in enumerate(resultados):
                        v_id_item = item.get('videoId')
                        if not v_id_item:
                            continue
                        
                        titulo = item.get('title', 'Canción desconocida')
                        artistas_list = item.get('artists', [])
                        artistas = ", ".join([a['name'] for a in artistas_list if 'name' in a]) or item.get('author', 'Artista')
                        duracion = item.get('duration', '')
                        thumbnails = item.get('thumbnails', [])
                        thumb_item = thumbnails[-1]['url'] if thumbnails else ""
                        
                        texto_opcion = f"➕  {titulo} — {artistas}" + (f" ({duracion})" if duracion else "")
                        
                        col_img, col_btn_song = st.columns([0.15, 0.85], vertical_alignment="center")
                        with col_img:
                            if thumb_item:
                                st.image(thumb_item, use_container_width=True)
                        with col_btn_song:
                            if st.button(texto_opcion, key=f"song_{v_id_item}_{idx}"):
                                tiempo_actual = time.time()
                                tiempo_transcurrido = tiempo_actual - st.session_state.last_added_time
                                
                                if tiempo_transcurrido < COOLDOWN_SECONDS:
                                    tiempo_restante = int(COOLDOWN_SECONDS - tiempo_transcurrido)
                                    minutos = tiempo_restante // 60
                                    segundos = tiempo_restante % 60
                                    st.warning(f"¡Espera un poco! Puedes pedir otra canción en {minutos}m {segundos}s.")
                                else:
                                    nueva_cancion = {
                                        'video_id': v_id_item,
                                        'title': titulo,
                                        'artist': artistas,
                                        'thumbnail': thumb_item,
                                        'color': obtener_color_aleatorio()
                                    }
                                    agregar_a_playlist(nueva_cancion)
                                    st.session_state.last_added_time = tiempo_actual
                                    st.toast(f"Añadida a la lista: {titulo}", icon="🎵")
                                    st.rerun()
                                
            except Exception as e:
                st.error(f"Error al realizar la búsqueda: {str(e)}")

# ---------------------------------------------------------
# COLUMNA DERECHA: LISTA DE ESPERA (COMPARTIDA)
# ---------------------------------------------------------
with col_queue:
    st.markdown("### Lista de espera")
    
    if not room.playlist:
        st.markdown(
            """
            <div style="background: rgba(255, 34, 34, 0.05); border: 1px dashed rgba(255, 34, 34, 0.3); border-radius: 14px; padding: 25px 15px; text-align: center; color: #aaaaaa; font-size: 0.9rem;">
                🎵 La lista está vacía.<br>¡Busca canciones y agrégalas para reproducir!
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        for idx, item in enumerate(room.playlist):
            es_actual = (idx == room.current_index)
            
            c_img, c_info, c_act1, c_act2 = st.columns([0.2, 0.52, 0.14, 0.14], vertical_alignment="center")
            
            with c_img:
                if item['thumbnail']:
                    st.image(item['thumbnail'], use_container_width=True)
            
            with c_info:
                color_texto = "#ff5555" if es_actual else "#f0f0f0"
                icono = "▶ " if es_actual else ""
                st.markdown(
                    f"<div style='line-height:1.2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>"
                    f"<span style='color:{color_texto}; font-weight:700; font-size:0.86rem;'>{icono}{item['title']}</span><br>"
                    f"<span style='color:#a0a0a0; font-size:0.76rem;'>{item['artist']}</span>"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            
            with c_act1:
                if not es_actual:
                    if st.button("▶", key=f"play_now_{idx}_{item['video_id']}"):
                        reproducir_indice(idx)
                        st.rerun()
            
            with c_act2:
                if st.button("❌", key=f"del_{idx}_{item['video_id']}"):
                    eliminar_de_playlist(idx)
                    st.rerun()
        
        st.write("")
        if st.button("🗑️ Limpiar lista", use_container_width=True):
            room.playlist = []
            room.current_index = -1
            st.rerun()

# ---------------------------------------------------------
# CÓDIGO QR ABAJO DEL TODO (PARA MODO FIESTA)
# ---------------------------------------------------------
st.markdown("<br><hr style='border:1px solid rgba(255,34,34,0.2);'><br>", unsafe_allow_html=True)

st.markdown("""
    <div class='qr-container'>
        <h2 style='color:#ff2222; margin-bottom:5px; font-weight:800;'>📱 ¡Escanea para poner tu música!</h2>
        <p style='color:#cccccc; font-size:0.95rem; margin-top:0;'>Apunta con la cámara de tu teléfono para entrar a la app. (1 canción cada 2 minutos)</p>
    </div>
""", unsafe_allow_html=True)

col_qr_left, col_qr_center, col_qr_right = st.columns([1, 1.2, 1])

with col_qr_center:
    url_app = st.text_input(
        "Enlace de tu aplicación:", 
        value="https://share.streamlit.io", 
        help="Cambia este enlace por la URL pública de tu web para actualizar el QR al instante.",
        key="app_url_input"
    )
    
    qr_code_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(url_app)}"
    
    st.markdown(
        f"""
        <div style="background-color: #ffffff; padding: 16px; border-radius: 16px; display: flex; justify-content: center; align-items: center; box-shadow: 0 0 20px rgba(255, 34, 34, 0.2); margin-top: 10px;">
            <img src="{qr_code_api}" style="width: 100%; max-width: 240px; height: auto; border-radius: 4px;">
        </div>
        <p style="text-align: center; color: #a0a0a0; font-size: 0.85rem; margin-top: 10px;">Escanea el código QR con tu celular</p>
        """,
        unsafe_allow_html=True
    )
