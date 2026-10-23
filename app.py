"""
MusicNow - Party Mode
Gramola colaborativa en tiempo real con Streamlit + YouTube Music.

Modos:
  * Invitado (por defecto): ve lo que suena, busca y pide canciones (con cooldown)
    y puede quitar de la cola las canciones que él mismo pidió.
  * Anfitrión (?host=<PIN> o PIN en la barra lateral): controla toda la cola,
    no tiene cooldown y puede elegir si su dispositivo es el "parlante".

Solo el/los dispositivo(s) anfitrión con audio activado reproducen sonido; los
teléfonos de los invitados funcionan como control remoto.
"""
from __future__ import annotations

import base64
import hmac
import html
import io
import json
import random
import re
import threading
import time
import uuid
from urllib.parse import quote

import qrcode
import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic

st.set_page_config(
    page_title="MusicNow - Party Mode",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# CONFIGURACIÓN (se puede sobreescribir en .streamlit/secrets.toml)
# ---------------------------------------------------------
def _secret(nombre: str, defecto):
    try:
        return st.secrets.get(nombre, defecto)
    except Exception:
        return defecto


APP_URL = str(_secret("APP_URL", "https://musicnowcl.streamlit.app"))
HOST_PIN = str(_secret("HOST_PIN", "1234"))
PIN_POR_DEFECTO = HOST_PIN == "1234"

COOLDOWN_SECONDS = 120
MAX_RESULTADOS = 5
MAX_COLA = 100
REFRESCO_ESTADO = "2s"
REFRESCO_COLA = "3s"
GUARDIA_FIN_SEG = 5  # ignora avisos de "terminó" que lleguen justo después de empezar

COLORES = [
    "#ff2222", "#00f0ff", "#a855f7", "#ec4899", "#ff9500", "#00ff88",
    "#3b82f6", "#ff206e", "#10b981", "#e11d48", "#8b5cf6", "#f59e0b",
]


def formatear_tiempo(segundos: float) -> str:
    segundos = max(0, int(segundos))
    return f"{segundos // 60}m {segundos % 60:02d}s"


def incrustar_html(codigo: str, alto: int):
    """Usa st.iframe (Streamlit nuevo) o components.html (versiones anteriores)."""
    if hasattr(st, "iframe"):
        st.iframe(codigo.strip(), height=alto)
    else:
        components.html(codigo, height=alto)


# ---------------------------------------------------------
# SALA COMPARTIDA GLOBALMENTE (thread-safe)
# ---------------------------------------------------------
class SharedPartyRoom:
    """Estado global de la fiesta. Todas las mutaciones pasan por el lock,
    porque Streamlit atiende a cada invitado en un hilo distinto."""

    def __init__(self):
        self.lock = threading.RLock()
        self.playlist: list[dict] = []
        self.current_index = -1
        self.finished = False
        self.started_at = 0.0
        self.last_request: dict[str, float] = {}

    # --- utilidades internas (llamar con el lock tomado) ---
    def _poner_actual(self, idx: int):
        self.current_index = idx
        self.finished = False
        self.started_at = time.time()

    def _indice(self, uid: str):
        for i, cancion in enumerate(self.playlist):
            if cancion["uid"] == uid:
                return i
        return None

    def _primer_pendiente(self) -> int:
        """Índice de la primera canción que aún no termina de sonar."""
        if self.current_index < 0:
            return 0
        return self.current_index + (1 if self.finished else 0)

    # --- lectura ---
    def snapshot(self):
        with self.lock:
            return [dict(c) for c in self.playlist], self.current_index, self.finished, self.started_at

    def cancion_actual(self):
        with self.lock:
            if not self.finished and 0 <= self.current_index < len(self.playlist):
                return dict(self.playlist[self.current_index])
            return None

    def ids_pendientes(self) -> set[str]:
        with self.lock:
            return {c["video_id"] for c in self.playlist[self._primer_pendiente():]}

    def cooldown_restante(self, invitado: str) -> float:
        with self.lock:
            ultimo = self.last_request.get(invitado, 0)
        return max(0.0, COOLDOWN_SECONDS - (time.time() - ultimo))

    # --- escritura ---
    def agregar(self, cancion: dict, invitado: str, es_host: bool) -> tuple[bool, str]:
        with self.lock:
            if not es_host:
                restante = self.cooldown_restante(invitado)
                if restante > 0:
                    return False, f"¡Espera un poco! Puedes pedir otra canción en {formatear_tiempo(restante)}."
            if cancion["video_id"] in self.ids_pendientes():
                return False, "Esa canción ya está en la lista 😉"
            if len(self.playlist) - self._primer_pendiente() >= MAX_COLA:
                return False, "La lista está llena. Espera a que suenen algunas canciones."

            self.playlist.append(cancion)
            empieza_ya = False
            if self.current_index == -1:
                self._poner_actual(0)
                empieza_ya = True
            elif self.finished:
                self._poner_actual(len(self.playlist) - 1)
                empieza_ya = True
            if not es_host:
                self.last_request[invitado] = time.time()

        if empieza_ya:
            return True, f"¡Sonando ahora: {cancion['title']}!"
        return True, f"Añadida a la lista: {cancion['title']}"

    def reproducir(self, uid: str):
        with self.lock:
            idx = self._indice(uid)
            if idx is not None:
                self._poner_actual(idx)

    def siguiente(self):
        with self.lock:
            if not self.playlist or self.finished:
                return
            if self.current_index < len(self.playlist) - 1:
                self._poner_actual(self.current_index + 1)
            else:
                self.finished = True

    def anterior(self):
        with self.lock:
            if not self.playlist:
                return
            if self.finished:
                self._poner_actual(self.current_index)  # vuelve a tocar la última
            elif self.current_index > 0:
                self._poner_actual(self.current_index - 1)

    def cancion_terminada(self):
        """Lo llama el reproductor del anfitrión cuando un tema termina (o falla)."""
        with self.lock:
            if self.finished or time.time() - self.started_at < GUARDIA_FIN_SEG:
                return
            if self.current_index < len(self.playlist) - 1:
                self._poner_actual(self.current_index + 1)
            else:
                self.finished = True

    def eliminar(self, uid: str):
        with self.lock:
            idx = self._indice(uid)
            if idx is None:
                return
            self.playlist.pop(idx)
            if not self.playlist:
                self.current_index, self.finished = -1, False
            elif idx < self.current_index:
                self.current_index -= 1  # la actual se corrió una posición
            elif idx == self.current_index and not self.finished:
                if idx < len(self.playlist):
                    self._poner_actual(idx)  # pasa a la que venía después
                else:
                    self.current_index, self.finished = len(self.playlist) - 1, True
            elif self.current_index >= len(self.playlist):
                self.current_index = len(self.playlist) - 1

    def limpiar(self):
        with self.lock:
            self.playlist.clear()
            self.current_index, self.finished, self.started_at = -1, False, 0.0


@st.cache_resource
def get_party_room() -> SharedPartyRoom:
    return SharedPartyRoom()


room = get_party_room()


# ---------------------------------------------------------
# IDENTIDAD DEL DISPOSITIVO Y MODO ANFITRIÓN
# ---------------------------------------------------------
def obtener_id_invitado() -> str:
    """ID persistente en la URL: sobrevive a recargas, así el cooldown no se
    salta con F5 (antes vivía en session_state y se perdía al recargar)."""
    gid = st.query_params.get("g", "")
    if not re.fullmatch(r"[0-9a-f]{12}", gid or ""):
        gid = uuid.uuid4().hex[:12]
        st.query_params["g"] = gid
    return gid


def pin_valido(pin: str) -> bool:
    return bool(pin) and hmac.compare_digest(str(pin), HOST_PIN)


GUEST_ID = obtener_id_invitado()
ES_HOST = pin_valido(st.query_params.get("host", ""))

with st.sidebar:
    st.markdown("### 🎛️ Modo anfitrión")
    if ES_HOST:
        st.success("Modo anfitrión activo")
        audio_aqui = st.toggle(
            "🔊 Este dispositivo reproduce la música",
            value=st.query_params.get("audio", "1") != "0",
            help="Actívalo solo en la TV o el computador conectado a los parlantes. "
                 "Desactívalo si usas el modo anfitrión desde tu teléfono como control.",
        )
        st.query_params["audio"] = "1" if audio_aqui else "0"
        if PIN_POR_DEFECTO:
            st.warning("Estás usando el PIN por defecto. Define `HOST_PIN` en los Secrets de la app.")
        if st.button("Salir del modo anfitrión", width="stretch"):
            for clave in ("host", "audio"):
                if clave in st.query_params:
                    del st.query_params[clave]
            st.rerun()
    else:
        audio_aqui = False
        st.caption("¿Eres quien pone la música en la TV o el parlante? Ingresa el PIN.")
        with st.form("host_form", border=False):
            pin_ingresado = st.text_input("PIN", type="password")
            if st.form_submit_button("Entrar como anfitrión", width="stretch"):
                if pin_valido(pin_ingresado):
                    st.query_params["host"] = pin_ingresado
                    st.rerun()
                else:
                    st.error("PIN incorrecto")

AUDIO_AQUI = ES_HOST and audio_aqui


# ---------------------------------------------------------
# YOUTUBE MUSIC
# ---------------------------------------------------------
@st.cache_resource
def get_ytmusic():
    try:
        return YTMusic()
    except Exception:
        return None


def mejor_miniatura(thumbnails: list[dict]) -> str:
    if not thumbnails:
        return ""
    url = thumbnails[-1].get("url", "")
    # Las carátulas de YT Music vienen en 60-120px; pedimos una más nítida para el vinilo
    return re.sub(r"=w\d+-h\d+", "=w400-h400", url)


@st.cache_data(ttl=900, show_spinner=False)
def buscar_canciones(consulta: str):
    """Devuelve una lista de canciones o None si no hay conexión con YT Music.
    Se cachea para no repetir la consulta en cada recarga de la página."""
    yt = get_ytmusic()
    if yt is None:
        return None
    resultados, vistos = [], set()
    for filtro in ("songs", "videos"):
        try:
            crudos = yt.search(consulta, filter=filtro, limit=MAX_RESULTADOS * 2) or []
        except Exception:
            crudos = []
        for item in crudos:
            vid = item.get("videoId")
            if not vid or vid in vistos:
                continue
            vistos.add(vid)
            artistas = ", ".join(a["name"] for a in (item.get("artists") or []) if a.get("name"))
            resultados.append({
                "video_id": vid,
                "title": item.get("title") or "Canción desconocida",
                "artist": artistas or item.get("author") or "Artista desconocido",
                "duration": item.get("duration") or "",
                "thumbnail": mejor_miniatura(item.get("thumbnails") or []),
            })
            if len(resultados) >= MAX_RESULTADOS:
                return resultados
    return resultados


def escapar_md(texto: str) -> str:
    """Las etiquetas de st.button interpretan Markdown; escapamos símbolos especiales."""
    return re.sub(r"([\\`*_\[\]{}()#+\-.!|~<>$])", r"\\\1", texto)


# ---------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------
def on_agregar(resultado: dict, invitado: str, es_host: bool):
    cancion = {
        **resultado,
        "uid": uuid.uuid4().hex,
        "color": random.choice(COLORES),
        "added_by": invitado,
        "added_at": time.time(),
    }
    ok, mensaje = room.agregar(cancion, invitado, es_host)
    st.session_state.flash = ("ok" if ok else "warn", mensaje)


def on_limpiar_confirmado():
    room.limpiar()
    st.session_state.confirmar_limpiar = False


def estado_codificado() -> str:
    """Estado actual en base64 (JSON) para que el reproductor lo lea del DOM."""
    playlist, idx, terminado, inicio = room.snapshot()
    actual = playlist[idx] if (not terminado and 0 <= idx < len(playlist)) else None
    siguiente = playlist[idx + 1]["title"] if actual and idx + 1 < len(playlist) else ""
    payload = {
        "token": f"{actual['uid']}:{inicio:.3f}" if actual else "",
        "vid": actual["video_id"] if actual else "",
        "title": actual["title"] if actual else "",
        "artist": actual["artist"] if actual else "",
        "thumb": actual["thumbnail"] if actual else "",
        "color": actual["color"] if actual else "#ff2222",
        "pos": idx + 1,
        "total": len(playlist),
        "next": siguiente,
    }
    return base64.b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode()


# ---------------------------------------------------------
# CSS GLOBAL
# ---------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');

.stApp { background-color: #0e0e10; color: #ffffff; font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; max-width: 1200px !important; }

.minimal-title {
    color: #ff2222; text-align: center; font-size: clamp(2.4rem, 8vw, 3.5rem);
    font-weight: 900; margin-bottom: 2px; letter-spacing: -1.5px;
}
.minimal-sub-wave {
    text-align: center; font-size: 1rem; font-weight: 700; margin: 0 0 25px 0;
    background: linear-gradient(90deg, #ff2222 0%, #ff2222 20%, #ff6b00 32%, #00f0ff 42%, #a855f7 52%, #ec4899 62%, #ff2222 75%, #ff2222 100%);
    background-size: 260% 100%;
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    animation: rgbWaveSweep 3.8s ease-in-out infinite alternate;
}
@keyframes rgbWaveSweep { 0% { background-position: 100% 0%; } 100% { background-position: 0% 0%; } }

/* Canal oculto entre Python y el reproductor */
.st-key-mn_state, .st-key-mn_ended { display: none !important; }

[data-testid="InputInstructions"], [data-testid="stInputInstructions"] { display: none !important; }

/* BARRA DE BÚSQUEDA */
div[data-testid="stForm"] {
    background-color: #16161a !important; border: 2px solid #ff2222 !important;
    border-radius: 14px !important; padding: 4px 8px !important;
    box-shadow: 0 0 12px rgba(255, 34, 34, 0.25) !important; transition: all 0.3s ease !important;
    margin: 10px 0 15px 0 !important;
}
div[data-testid="stForm"]:focus-within { border-color: #ff5555 !important; box-shadow: 0 0 18px rgba(255, 34, 34, 0.45) !important; }
div[data-testid="stForm"] div[data-testid="stTextInput"] > div > div { background-color: transparent !important; border: none !important; box-shadow: none !important; }
div[data-testid="stForm"] div[data-testid="stTextInput"] input { background-color: transparent !important; color: #ffffff !important; font-size: 0.95rem !important; }
div[data-testid="stForm"] button { border-radius: 10px !important; background-color: #ff2222 !important; border: none !important; color: #fff !important; font-weight: 700 !important; }
div[data-testid="stForm"] button:hover { background-color: #ff4444 !important; box-shadow: 0 0 14px rgba(255, 34, 34, 0.6) !important; }
[data-testid="stSidebar"] div[data-testid="stForm"] { border-width: 1px !important; }

/* BOTONES GENERALES */
div.stButton > button {
    background-color: #16161a; color: #e0e0e0; font-size: 0.9rem; font-weight: 500;
    border: 1px solid #2a2a30; border-radius: 12px; transition: all 0.2s ease; justify-content: flex-start;
}
div.stButton > button:hover:enabled { background-color: #ff2222 !important; border-color: #ff2222 !important; color: #fff !important; transform: translateY(-1px); }
div.stButton > button:disabled { opacity: 0.55; }

div[data-testid="stImage"] img { border-radius: 8px !important; object-fit: cover !important; aspect-ratio: 1 / 1; }

h3 { color: #ffffff !important; font-size: 1.1rem !important; font-weight: 700 !important; margin: 5px 0 12px 0 !important; }

/* PANEL LISTA DE ESPERA (por key, ya no afecta a otras columnas) */
.st-key-queue_panel {
    background: rgba(255, 34, 34, 0.05); border: 1px solid rgba(255, 34, 34, 0.25);
    border-radius: 18px; padding: 18px 16px;
    box-shadow: 0 8px 32px rgba(255, 0, 0, 0.15), inset 0 0 15px rgba(255, 34, 34, 0.03);
}
.st-key-queue_panel div[data-testid="stHorizontalBlock"] {
    background: rgba(22, 22, 26, 0.65); border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px; padding: 6px 10px; margin-bottom: 4px; transition: all 0.25s ease;
}
.st-key-queue_panel div[data-testid="stHorizontalBlock"]:hover { background: rgba(255, 34, 34, 0.15); border-color: rgba(255, 34, 34, 0.35); }
.st-key-queue_panel div.stButton > button { padding: 4px 6px !important; font-size: 0.8rem !important; border-radius: 8px !important; min-height: 34px !important; justify-content: center; }

.queue-title { line-height: 1.25; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.queue-title b { font-size: 0.86rem; }
.queue-title small { color: #a0a0a0; font-size: 0.76rem; }
.queue-tag { font-size: 0.68rem; font-weight: 800; letter-spacing: 0.06em; color: #ff5555; text-transform: uppercase; }

.qr-container {
    background: rgba(22, 22, 26, 0.8); border: 1px solid rgba(255, 34, 34, 0.3);
    border-radius: 20px; padding: 20px; text-align: center;
    box-shadow: 0 0 25px rgba(255, 34, 34, 0.15); margin-top: 25px;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# REPRODUCTOR (iframe persistente: su HTML no cambia entre recargas,
# por eso no se reinicia el audio; lee el estado desde el DOM)
# ---------------------------------------------------------
PLAYER_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
<style>
  :root { --accent: #ff2222; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 10px; background: transparent; color: #fff;
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
    display: flex; flex-direction: column; align-items: center;
  }
  .stage { position: relative; margin: 4px 0 14px; }
  .vinyl {
    width: 180px; height: 180px; border-radius: 50%; cursor: pointer;
    display: flex; justify-content: center; align-items: center;
    background: radial-gradient(circle at center, transparent 38%, rgba(0,0,0,0.85) 39%, transparent 40%),
                repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #222 3px, #141414 4px),
                conic-gradient(from 45deg, #050505, #3d3d3d 22deg, #050505 45deg, #050505 225deg, #3d3d3d 247deg, #050505 270deg);
    box-shadow: 0 6px 20px rgba(0,0,0,0.8), 0 0 18px var(--accent);
    border: 1px solid #1a1a1a; transition: box-shadow 0.6s ease;
  }
  .label {
    width: 74px; height: 74px; border-radius: 50%;
    background: var(--accent) center / cover no-repeat; border: 2px solid var(--accent);
    display: flex; justify-content: center; align-items: center;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 0 8px var(--accent);
  }
  .hole { width: 10px; height: 10px; background: #fff; border-radius: 50%; box-shadow: inset 0 0 2px rgba(0,0,0,0.8); }
  .spin { animation: spin 2.4s linear infinite; }
  .spin.paused { animation-play-state: paused; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .unlock {
    position: absolute; inset: 0; border-radius: 50%; border: 2px solid var(--accent);
    background: rgba(0,0,0,0.78); color: #fff; font: 800 0.85rem inherit; font-family: inherit;
    cursor: pointer; display: none; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  }
  .unlock.show { display: flex; animation: pulse 1.4s ease-in-out infinite; }
  @keyframes pulse { 50% { box-shadow: 0 0 22px var(--accent); } }

  .card {
    width: 100%; max-width: 460px; background: #16161a; border: 1px solid #2a2a30;
    border-radius: 16px; padding: 14px 18px; box-shadow: 0 0 20px rgba(0,0,0,0.6);
  }
  .title, .artist { text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .title { font-weight: 700; font-size: 0.98rem; }
  .artist { color: #a0a0a0; font-size: 0.82rem; margin-top: 2px; }
  .meta { text-align: center; color: #777; font-size: 0.74rem; margin-top: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .progress-row { display: flex; align-items: center; gap: 10px; margin: 12px 0; }
  .time { font-size: 0.78rem; color: #a0a0a0; min-width: 38px; font-variant-numeric: tabular-nums; }
  input[type=range] {
    -webkit-appearance: none; appearance: none; height: 5px; border-radius: 5px;
    background: #33333d; outline: none; cursor: pointer;
  }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none; width: 13px; height: 13px; border-radius: 50%;
    background: var(--accent); box-shadow: 0 0 8px var(--accent);
  }
  input[type=range]::-moz-range-thumb { width: 13px; height: 13px; border: none; border-radius: 50%; background: var(--accent); }
  #progress { flex: 1; }
  .controls { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .btn-play {
    background: var(--accent); color: #fff; border: none; border-radius: 50px; padding: 8px 22px;
    font-size: 0.9rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 8px;
    transition: transform 0.2s ease; box-shadow: 0 0 10px var(--accent);
  }
  .btn-play:hover { transform: scale(1.04); }
  .vol { display: flex; align-items: center; gap: 8px; color: #a0a0a0; font-size: 0.85rem; }
  #volume { width: 90px; }

  .remote { text-align: center; color: #8a8a95; font-size: 0.8rem; margin-top: 10px; }
  .eq { display: inline-flex; gap: 2px; height: 10px; align-items: flex-end; margin-right: 6px; }
  .eq i { width: 3px; background: var(--accent); animation: eq 0.9s ease-in-out infinite; }
  .eq i:nth-child(2) { animation-delay: 0.2s; } .eq i:nth-child(3) { animation-delay: 0.4s; }
  @keyframes eq { 0%,100% { height: 3px; } 50% { height: 10px; } }

  .empty { color: #777; font-size: 0.9rem; text-align: center; margin-top: 6px; }
  .notice { color: #ffb020; font-size: 0.78rem; text-align: center; min-height: 1em; margin-top: 8px; }
  #yt-wrap { position: absolute; width: 200px; height: 200px; top: 0; left: 0; opacity: 0.001; pointer-events: none; z-index: -1; }
</style>
</head>
<body>
  <div id="yt-wrap"><div id="yt-player"></div></div>

  <div class="stage">
    <div id="vinyl" class="vinyl"><div id="label" class="label"><div class="hole"></div></div></div>
    <button id="unlock" class="unlock"><i class="fas fa-volume-high fa-xl"></i>Toca para activar<br>el sonido</button>
  </div>

  <div id="empty" class="empty">Agrega una canción a la lista para comenzar 🎶</div>

  <div id="card" class="card" style="display:none">
    <div id="title" class="title"></div>
    <div id="artist" class="artist"></div>
    <div id="host-controls">
      <div class="progress-row">
        <span id="cur" class="time">0:00</span>
        <input id="progress" type="range" min="0" max="1000" value="0">
        <span id="dur" class="time">0:00</span>
      </div>
      <div class="controls">
        <button id="play" class="btn-play"><i id="play-icon" class="fas fa-play"></i><span id="play-text">Play</span></button>
        <div class="vol"><i class="fas fa-volume-high"></i><input id="volume" type="range" min="0" max="100" value="100"></div>
      </div>
    </div>
    <div id="remote" class="remote"><span class="eq"><i></i><i></i><i></i></span>Suena en el equipo del anfitrión</div>
    <div id="meta" class="meta"></div>
  </div>
  <div id="notice" class="notice"></div>

<script>
  const AUDIO = __AUDIO__;
  const PARENT = window.parent.document;
  const $ = (id) => document.getElementById(id);

  let player = null, ready = false, loadedToken = "", endedFor = "", seeking = false, unlockTimer = null;

  if (AUDIO) { $('remote').style.display = 'none'; } else { $('host-controls').style.display = 'none'; }

  // ---- Lectura del estado publicado por Streamlit ----
  function readState() {
    const box = PARENT.querySelector('.st-key-mn_state');
    if (!box) return null;
    const m = (box.textContent || '').match(/[A-Za-z0-9+\/=]{16,}/);
    if (!m) return null;
    try {
      const bin = atob(m[0]);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return JSON.parse(new TextDecoder().decode(bytes));
    } catch (e) { return null; }
  }

  function setSpinning(on, paused) {
    const v = $('vinyl');
    v.classList.toggle('spin', on);
    v.classList.toggle('paused', !!paused);
  }

  function applyUI(s) {
    const has = !!s.vid;
    document.documentElement.style.setProperty('--accent', s.color || '#ff2222');
    $('empty').style.display = has ? 'none' : 'block';
    $('empty').textContent = s.total ? 'La lista terminó. ¡Agrega más canciones! 🎶'
                                     : 'Agrega una canción a la lista para comenzar 🎶';
    $('card').style.display = has ? 'block' : 'none';
    $('title').textContent = s.title || '';
    $('artist').textContent = s.artist || '';
    $('meta').textContent = has ? ('Canción ' + s.pos + ' de ' + s.total + (s.next ? ' · Sigue: ' + s.next : '')) : '';
    $('label').style.backgroundImage = s.thumb ? 'url(' + JSON.stringify(s.thumb) + ')' : 'none';
    if (!AUDIO) setSpinning(has, false);
  }

  function sync() {
    const s = readState();
    if (!s) return;
    applyUI(s);
    if (!AUDIO || !ready) return;
    if (s.token && s.token !== loadedToken) {
      loadedToken = s.token;
      $('notice').textContent = '';
      resetProgress();
      player.loadVideoById(s.vid);
      armUnlockCheck();
    } else if (!s.token && loadedToken) {
      loadedToken = '';
      player.stopVideo();
      setSpinning(false);
      resetProgress();
    }
  }

  // ---- Reproductor de YouTube (solo en el dispositivo anfitrión con audio) ----
  if (AUDIO) {
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
  }

  window.onYouTubeIframeAPIReady = function () {
    player = new YT.Player('yt-player', {
      height: '200', width: '200',
      playerVars: { autoplay: 1, controls: 0, disablekb: 1, fs: 0, rel: 0, playsinline: 1, iv_load_policy: 3 },
      events: {
        onReady: () => { ready = true; player.setVolume(+$('volume').value); sync(); },
        onStateChange: onState,
        onError: onError,
      },
    });
  };

  function setPlaying(playing) {
    setSpinning(true, !playing);
    $('play-icon').className = playing ? 'fas fa-pause' : 'fas fa-play';
    $('play-text').textContent = playing ? 'Pausa' : 'Play';
  }

  function onState(e) {
    if (e.data === YT.PlayerState.PLAYING) { setPlaying(true); hideUnlock(); }
    else if (e.data === YT.PlayerState.ENDED) { setPlaying(false); signalEnded(); }
    else if (e.data !== YT.PlayerState.BUFFERING) { setPlaying(false); }
  }

  function onError() {
    // 101/150: el dueño no permite incrustarlo; 100: video eliminado
    $('notice').textContent = '⚠️ Esta canción no se puede reproducir aquí. Saltando…';
    setTimeout(signalEnded, 1500);
  }

  // Avisa a Python pulsando un botón oculto (solo si sigue siendo la misma canción)
  function signalEnded() {
    const s = readState();
    if (!s || !loadedToken || s.token !== loadedToken || endedFor === loadedToken) return;
    endedFor = loadedToken;
    const btn = PARENT.querySelector('.st-key-mn_ended button');
    if (btn) btn.click();
  }

  // ---- Política de autoplay del navegador ----
  function armUnlockCheck() {
    clearTimeout(unlockTimer);
    unlockTimer = setTimeout(() => {
      const st = player && player.getPlayerState ? player.getPlayerState() : -1;
      if (loadedToken && st !== 1 && st !== 3 && st !== 2) $('unlock').classList.add('show');
    }, 3000);
  }
  function hideUnlock() { clearTimeout(unlockTimer); $('unlock').classList.remove('show'); }
  $('unlock').addEventListener('click', () => { if (player) player.playVideo(); hideUnlock(); });

  function togglePlay() {
    if (!AUDIO || !player || !player.getPlayerState || !loadedToken) return;
    const st = player.getPlayerState();
    if (st === 1 || st === 3) player.pauseVideo(); else player.playVideo();
  }
  $('play').addEventListener('click', togglePlay);
  $('vinyl').addEventListener('click', togglePlay);

  // ---- Progreso y volumen ----
  function fmt(sec) { sec = Math.floor(sec || 0); return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0'); }
  function paint(el, pct) { el.style.background = 'linear-gradient(to right, var(--accent) ' + pct + '%, #33333d ' + pct + '%)'; }
  function resetProgress() { $('progress').value = 0; paint($('progress'), 0); $('cur').textContent = '0:00'; $('dur').textContent = '0:00'; }

  $('progress').addEventListener('input', (e) => {
    seeking = true;
    paint(e.target, e.target.value / 10);
    if (player && player.getDuration) $('cur').textContent = fmt(e.target.value / 1000 * player.getDuration());
  });
  $('progress').addEventListener('change', (e) => {
    if (player && player.getDuration) {
      const d = player.getDuration();
      if (d > 0) player.seekTo(e.target.value / 1000 * d, true);
    }
    seeking = false;
  });
  $('volume').addEventListener('input', (e) => {
    if (player && player.setVolume) player.setVolume(+e.target.value);
    paint(e.target, e.target.value);
  });
  paint($('volume'), 100);

  setInterval(() => {
    if (!AUDIO || !ready || !loadedToken || seeking || !player.getDuration) return;
    const cur = player.getCurrentTime(), dur = player.getDuration();
    if (dur > 0) {
      const pct = (cur / dur) * 100;
      $('progress').value = pct * 10;
      paint($('progress'), pct);
      $('cur').textContent = fmt(cur);
      $('dur').textContent = fmt(dur);
    }
  }, 500);

  setInterval(sync, 1000);
  sync();
</script>
</body>
</html>
"""


# ---------------------------------------------------------
# ENCABEZADO
# ---------------------------------------------------------
st.markdown("<h1 class='minimal-title'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown("<p class='minimal-sub-wave'>Busca una canción y añádela a la lista</p>", unsafe_allow_html=True)

st.session_state.setdefault("current_query", "")
st.session_state.setdefault("confirmar_limpiar", False)


# ---------------------------------------------------------
# FRAGMENTOS EN VIVO
# ---------------------------------------------------------
@st.fragment(run_every=REFRESCO_ESTADO)
def panel_estado():
    # Canal de datos oculto que lee el reproductor
    with st.container(key="mn_state"):
        st.text(estado_codificado())
    if AUDIO_AQUI:
        st.button("ended", key="mn_ended", on_click=room.cancion_terminada)

    if ES_HOST:
        playlist, idx, terminado, _ = room.snapshot()
        if playlist:
            c_prev, c_next = st.columns(2)
            with c_prev:
                st.button("⏮️ Anterior", on_click=room.anterior, width="stretch",
                          disabled=(idx <= 0 and not terminado))
            with c_next:
                st.button("Siguiente ⏭️", on_click=room.siguiente, width="stretch",
                          disabled=terminado)


def fila_cancion(cancion: dict, etiqueta: str = "", reproducir: bool = True):
    c_img, c_info, c_a1, c_a2 = st.columns([0.18, 0.54, 0.14, 0.14], vertical_alignment="center")
    with c_img:
        if cancion.get("thumbnail"):
            st.image(cancion["thumbnail"], width=52)
    with c_info:
        tag = f"<div class='queue-tag'>{html.escape(etiqueta)}</div>" if etiqueta else ""
        mia = " · tu pedido" if cancion.get("added_by") == GUEST_ID and not ES_HOST else ""
        st.markdown(
            f"<div class='queue-title'>{tag}<b>{html.escape(cancion['title'])}</b><br>"
            f"<small>{html.escape(cancion['artist'])}{mia}</small></div>",
            unsafe_allow_html=True,
        )
    with c_a1:
        if ES_HOST and reproducir:
            st.button("▶", key=f"play_{cancion['uid']}", help="Reproducir ahora",
                      on_click=room.reproducir, args=(cancion["uid"],))
    with c_a2:
        if ES_HOST or cancion.get("added_by") == GUEST_ID:
            st.button("✕", key=f"del_{cancion['uid']}", help="Quitar de la lista",
                      on_click=room.eliminar, args=(cancion["uid"],))


@st.fragment(run_every=REFRESCO_COLA)
def panel_cola():
    playlist, idx, terminado, _ = room.snapshot()
    st.markdown("### Lista de espera")

    if not playlist:
        st.markdown(
            """<div style="background: rgba(255,34,34,0.05); border: 1px dashed rgba(255,34,34,0.3);
            border-radius: 14px; padding: 25px 15px; text-align: center; color: #aaa; font-size: 0.9rem;">
            🎵 La lista está vacía.<br>¡Busca canciones y agrégalas para reproducir!</div>""",
            unsafe_allow_html=True,
        )
        return

    if not terminado and 0 <= idx < len(playlist):
        fila_cancion(playlist[idx], "▶ Sonando ahora", reproducir=False)
        proximas = playlist[idx + 1:]
        historial = playlist[:idx]
    else:
        proximas, historial = [], playlist

    if proximas:
        st.caption(f"A continuación · {len(proximas)}")
        for n, cancion in enumerate(proximas, start=1):
            fila_cancion(cancion, f"#{n}")
    else:
        st.caption("No hay más canciones en espera. ¡Pide la próxima! 🎶")

    if historial:
        with st.expander(f"Ya sonaron ({len(historial)})"):
            for cancion in reversed(historial):
                fila_cancion(cancion)

    if ES_HOST:
        if not st.session_state.confirmar_limpiar:
            if st.button("🗑️ Limpiar lista", width="stretch"):
                st.session_state.confirmar_limpiar = True
                st.rerun(scope="fragment")
        else:
            st.warning("¿Borrar toda la lista?")
            c_si, c_no = st.columns(2)
            c_si.button("Sí, borrar", on_click=on_limpiar_confirmado, width="stretch")
            if c_no.button("Cancelar", width="stretch"):
                st.session_state.confirmar_limpiar = False
                st.rerun(scope="fragment")


# ---------------------------------------------------------
# COLUMNAS REPRODUCTOR + LISTA
# ---------------------------------------------------------
col_main, col_queue = st.columns([1.55, 1.05], gap="large")

with col_main:
    # El HTML es constante por dispositivo => el iframe no se recarga y la música no se corta
    incrustar_html(PLAYER_TEMPLATE.replace("__AUDIO__", "true" if AUDIO_AQUI else "false"), 440)
    panel_estado()

    # FORMULARIO DE BÚSQUEDA
    with st.form(key="search_form", border=False):
        col_input, col_btn = st.columns([0.78, 0.22], vertical_alignment="center")
        with col_input:
            query_input = st.text_input(
                "Búsqueda", placeholder="Buscar canción, artista o género...",
                label_visibility="collapsed", max_chars=100,
            )
        with col_btn:
            btn_buscar = st.form_submit_button("Buscar", width="stretch")

    if btn_buscar and query_input.strip():
        st.session_state.current_query = query_input.strip()

    flash = st.session_state.pop("flash", None)
    if flash:
        tipo, mensaje = flash
        if tipo == "ok":
            st.toast(mensaje, icon="🎵")
        else:
            st.warning(mensaje)

    # RESULTADOS DE BÚSQUEDA
    if st.session_state.current_query:
        st.write("### Sugerencias")
        with st.spinner("Buscando en YouTube Music…"):
            try:
                resultados = buscar_canciones(st.session_state.current_query)
                error = None
            except Exception as e:  # noqa: BLE001
                resultados, error = [], str(e)

        if error:
            st.error(f"Error al realizar la búsqueda: {error}")
        elif resultados is None:
            st.error("No se pudo conectar a YouTube Music. Intenta de nuevo en un momento.")
        elif not resultados:
            st.info("No se encontraron resultados para tu búsqueda.")
        else:
            if not ES_HOST:
                restante = room.cooldown_restante(GUEST_ID)
                if restante > 0:
                    st.caption(f"⏳ Podrás pedir otra canción en {formatear_tiempo(restante)}.")
            en_cola = room.ids_pendientes()

            for r in resultados:
                ya_esta = r["video_id"] in en_cola
                texto = f"{r['title']} — {r['artist']}" + (f" ({r['duration']})" if r["duration"] else "")
                etiqueta = ("✓  " if ya_esta else "➕  ") + escapar_md(texto)

                col_img, col_btn_song = st.columns([0.15, 0.85], vertical_alignment="center")
                with col_img:
                    if r["thumbnail"]:
                        st.image(r["thumbnail"], width=56)
                with col_btn_song:
                    st.button(
                        etiqueta, key=f"add_{r['video_id']}", width="stretch",
                        disabled=ya_esta, help="Ya está en la lista" if ya_esta else "Agregar a la lista",
                        on_click=on_agregar, args=(r, GUEST_ID, ES_HOST),
                    )

with col_queue:
    with st.container(key="queue_panel"):
        panel_cola()


# ---------------------------------------------------------
# QR Y COMPARTIR
# ---------------------------------------------------------
st.markdown("<br><hr style='border:1px solid rgba(255,34,34,0.2);'>", unsafe_allow_html=True)
st.markdown("""
<div class='qr-container'>
    <h2 style='color:#ff2222; margin-bottom:5px; font-weight:800;'>📱 ¡Escanea o comparte para poner tu música!</h2>
    <p style='color:#cccccc; font-size:0.95rem; margin-top:0;'>Apunta con la cámara de tu teléfono o comparte el enlace por WhatsApp.</p>
</div>
""", unsafe_allow_html=True)


@st.cache_data
def generar_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


QR_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
<style>
  body { background: transparent; color: #fff; font-family: 'Inter', system-ui, -apple-system, sans-serif; text-align: center; margin: 0; padding: 10px; }
  .qr-box { background: #fff; padding: 14px; border-radius: 16px; display: inline-block; box-shadow: 0 0 20px rgba(255,34,34,0.25); }
  .qr-box img { display: block; width: 190px; height: 190px; image-rendering: pixelated; }
  .url { color: #a0a0a0; font-size: 0.85rem; margin-top: 12px; word-break: break-all; }
  .row { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 12px; }
  .btn { border: none; border-radius: 10px; padding: 10px 18px; font-size: 0.9rem; font-weight: 700; cursor: pointer;
         display: inline-flex; align-items: center; gap: 8px; text-decoration: none; color: #fff; font-family: inherit; }
  .wa { background: #25D366; box-shadow: 0 4px 12px rgba(37,211,102,0.3); }
  .copy { background: #2a2a30; }
</style>
</head>
<body>
  <div class="qr-box"><img src="data:image/png;base64,__QR__" alt="Código QR para entrar a la fiesta"></div>
  <div class="url">__URL_TEXT__</div>
  <div class="row">
    <a class="btn wa" href="__WA__" target="_blank" rel="noopener"><i class="fab fa-whatsapp"></i> Enviar por WhatsApp</a>
    <button class="btn copy" id="copy"><i class="fas fa-link"></i> <span id="copy-text">Copiar enlace</span></button>
  </div>
<script>
  const URL_APP = __URL_JSON__;
  const label = document.getElementById('copy-text');
  function done(ok) {
    label.textContent = ok ? '¡Copiado!' : 'No se pudo copiar';
    setTimeout(() => { label.textContent = 'Copiar enlace'; }, 2000);
  }
  document.getElementById('copy').addEventListener('click', () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(URL_APP).then(() => done(true)).catch(fallback);
    } else { fallback(); }
  });
  function fallback() {
    const t = document.createElement('textarea');
    t.value = URL_APP; document.body.appendChild(t); t.select();
    let ok = false; try { ok = document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(t); done(ok);
  }
</script>
</body>
</html>
"""

mensaje_wa = f"🎉 ¡Pide tu canción para la fiesta en MusicNow! {APP_URL}"
html_qr = (
    QR_TEMPLATE
    .replace("__QR__", generar_qr_base64(APP_URL))
    .replace("__URL_TEXT__", html.escape(APP_URL))
    .replace("__WA__", html.escape("https://wa.me/?text=" + quote(mensaje_wa)))
    .replace("__URL_JSON__", json.dumps(APP_URL))
)
incrustar_html(html_qr, 340)
