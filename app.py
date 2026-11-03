"""
MusicNow - Party Mode
Gramola colaborativa en tiempo real con Streamlit + YouTube Music.

  * Todos (admin e invitados) ven y pueden ESCUCHAR lo mismo, sincronizado:
    el servidor lleva el reloj de la canción y cada dispositivo se ajusta a él.
  * Invitados: escuchan, piden canciones (1 cada 2 minutos) y quitan las suyas.
  * Admin (PIN): pausa, adelanta/retrocede, cambia de canción y maneja la cola.
"""
from __future__ import annotations

import base64
import concurrent.futures as cf
import hmac
import html
import io
import json
import math
import random
import re
import threading
import time
import unicodedata
import uuid
from urllib.parse import quote

import qrcode
import requests  # ya viene instalado con ytmusicapi
import streamlit as st
import streamlit.components.v1 as components
from ytmusicapi import YTMusic

st.set_page_config(
    page_title="MusicNow · Party Mode",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CONFIGURACIÓN (Settings → Secrets)
# =========================================================
def _secret(nombre: str, defecto):
    try:
        return st.secrets.get(nombre, defecto)
    except Exception:
        return defecto


APP_URL = str(_secret("APP_URL", "https://musicnowcl.streamlit.app"))
HOST_PIN = str(_secret("HOST_PIN", "1234"))
PIN_POR_DEFECTO = HOST_PIN == "1234"

# Súbelo cada vez que cambies la clase PartyRoom: obliga a Streamlit a crear
# una sala nueva en vez de reutilizar la antigua guardada en caché.
ROOM_VERSION = 5

COOLDOWN_SECONDS = 120
MAX_RESULTADOS = 10
ALTO_RESULTADOS = 340  # alto (px) del mini scroll de resultados
MAX_ALTERNATIVAS = 6  # versiones de respaldo por canción (para celulares)
MAX_VERIFICAR = 14    # grupos de resultados cuya reproducibilidad se comprueba
EMBED_TTL = 6 * 3600  # cuánto se recuerda si un video se puede incrustar
MAX_COLA = 100
REFRESCO_ESTADO = "2s"
REFRESCO_COLA = "3s"
GUARDIA_FIN_SEG = 5

COLORES = [
    "#ff2222", "#00f0ff", "#a855f7", "#ec4899", "#ff9500", "#00ff88",
    "#3b82f6", "#ff206e", "#10b981", "#e11d48", "#8b5cf6", "#f59e0b",
]


def formatear_tiempo(segundos: float) -> str:
    segundos = max(0, int(segundos))
    return f"{segundos // 60}m {segundos % 60:02d}s"


def incrustar_html(codigo: str, alto: int):
    """st.iframe en Streamlit nuevo; components.html en versiones anteriores."""
    if hasattr(st, "iframe"):
        st.iframe(codigo.strip(), height=alto)
    else:
        components.html(codigo, height=alto)


# =========================================================
# SALA COMPARTIDA (thread-safe) CON RELOJ DE REPRODUCCIÓN
# =========================================================
class PartyRoom:
    """El servidor es el reloj: guarda en qué segundo va la canción
    (anchor = momento en que habría empezado) y si está en pausa."""

    def __init__(self):
        self.lock = threading.RLock()
        self.playlist: list[dict] = []
        self.current_index = -1
        self.finished = False
        self.anchor = 0.0
        self.paused_pos: float | None = None
        self.epoch = 0
        self.last_request: dict[str, float] = {}

    # ---------- internos (con lock tomado) ----------
    def _poner_actual(self, idx: int):
        self.current_index = idx
        self.finished = False
        self.anchor = time.time()
        self.paused_pos = None
        self.epoch += 1

    def _actual(self):
        if not self.finished and 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def _token(self) -> str:
        actual = self._actual()
        return f"{actual['uid']}:{self.epoch}" if actual else ""

    def _posicion(self) -> float:
        if self.paused_pos is not None:
            return self.paused_pos
        return max(0.0, time.time() - self.anchor)

    def _indice(self, uid: str):
        for i, c in enumerate(self.playlist):
            if c["uid"] == uid:
                return i
        return None

    def _primer_pendiente(self) -> int:
        if self.current_index < 0:
            return 0
        return self.current_index + (1 if self.finished else 0)

    def _avanzar(self):
        if self.current_index < len(self.playlist) - 1:
            self._poner_actual(self.current_index + 1)
        else:
            self.finished = True
            self.paused_pos = None

    # ---------- lectura ----------
    def snapshot(self):
        with self.lock:
            return [dict(c) for c in self.playlist], self.current_index, self.finished

    def ids_pendientes(self) -> set[str]:
        with self.lock:
            return {c["video_id"] for c in self.playlist[self._primer_pendiente():]}

    def cooldown_restante(self, invitado: str) -> float:
        with self.lock:
            ultimo = self.last_request.get(invitado, 0)
        return max(0.0, COOLDOWN_SECONDS - (time.time() - ultimo))

    def estado(self) -> dict:
        with self.lock:
            actual = self._actual()
            idx, total = self.current_index, len(self.playlist)
            siguiente = self.playlist[idx + 1]["title"] if actual and idx + 1 < total else ""
            return {
                "token": self._token(),
                "vid": actual["video_id"] if actual else "",
                "title": actual["title"] if actual else "",
                "artist": actual["artist"] if actual else "",
                "thumb": actual["thumbnail"] if actual else "",
                "color": actual["color"] if actual else "#ff2222",
                "dur": actual.get("dur", 0) if actual else 0,
                "alts": actual.get("alts", []) if actual else [],
                "alts_rev": actual.get("alts_rev", 0) if actual else 0,
                "buscando": bool(actual.get("buscando")) if actual else False,
                "pos": idx + 1,
                "total": total,
                "next": siguiente,
                "can_prev": bool(self.playlist) and (self.finished or idx > 0),
                "can_next": bool(actual),
                "now": time.time(),
                "anchor": self.anchor,
                "paused": self.paused_pos is not None,
                "ppos": self.paused_pos or 0.0,
            }

    # ---------- escritura ----------
    def tick(self):
        """Avanza solo si la canción ya terminó según su duración
        (funciona aunque nadie tenga el reproductor abierto)."""
        with self.lock:
            actual = self._actual()
            if actual and self.paused_pos is None and actual.get("dur", 0) > 0:
                if self._posicion() > actual["dur"] + 3:
                    self._avanzar()

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
            empieza_ya = self.current_index == -1 or self.finished
            if empieza_ya:
                self._poner_actual(len(self.playlist) - 1)
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

    def eliminar(self, uid: str):
        with self.lock:
            idx = self._indice(uid)
            if idx is None:
                return
            self.playlist.pop(idx)
            if not self.playlist:
                self.current_index, self.finished = -1, False
            elif idx < self.current_index:
                self.current_index -= 1
            elif idx == self.current_index and not self.finished:
                if idx < len(self.playlist):
                    self._poner_actual(idx)
                else:
                    self.current_index, self.finished = len(self.playlist) - 1, True
            elif self.current_index >= len(self.playlist):
                self.current_index = len(self.playlist) - 1

    def pedir_mas_versiones(self, tok: str):
        """Un dispositivo no pudo con ninguna versión: se buscan más (máx. 3 rondas)."""
        with self.lock:
            actual = self._actual()
            if not actual or tok != self._token() or actual.get("buscando"):
                return None
            if actual.get("rondas", 0) >= 3:
                return None
            actual["rondas"] = actual.get("rondas", 0) + 1
            actual["buscando"] = True
            return dict(actual)

    def sumar_alternativas(self, uid: str, nuevos: list[str]):
        with self.lock:
            idx = self._indice(uid)
            if idx is None:
                return
            c = self.playlist[idx]
            existentes = {c["video_id"], *c.get("alts", [])}
            c["alts"] = c.get("alts", []) + [v for v in nuevos if v not in existentes]
            c["buscando"] = False
            c["alts_rev"] = c.get("alts_rev", 0) + 1

    def limpiar(self):
        with self.lock:
            self.playlist.clear()
            self.current_index, self.finished = -1, False
            self.paused_pos = None

    def comando(self, cmd: dict, es_host: bool):
        """Órdenes enviadas por los reproductores. Los invitados solo pueden
        avisar que la canción terminó o falló; el resto es exclusivo del admin."""
        c = cmd.get("c")
        with self.lock:
            actual = self._actual()

            if c in ("ended", "skip"):
                if not actual or cmd.get("tok") != self._token():
                    return  # aviso viejo o repetido: se ignora
                pos, dur = self._posicion(), actual.get("dur", 0)
                if c == "ended":
                    if pos < GUARDIA_FIN_SEG or (dur and pos < dur - 10 and not es_host):
                        return
                elif not es_host:
                    return  # un invitado que no puede reproducir NO salta la canción a todos
                self._avanzar()
                return

            if not es_host:
                return

            if c == "next" and self.playlist and not self.finished:
                self._avanzar()
            elif c == "prev" and self.playlist:
                if self.finished:
                    self._poner_actual(self.current_index)
                elif self._posicion() > 5 or self.current_index == 0:
                    self._poner_actual(self.current_index)  # vuelve al inicio
                else:
                    self._poner_actual(self.current_index - 1)
            elif c == "pause" and actual and self.paused_pos is None:
                self.paused_pos = self._posicion()
            elif c == "play" and actual and self.paused_pos is not None:
                self.anchor = time.time() - self.paused_pos
                self.paused_pos = None
            elif c == "seek" and actual:
                try:
                    t = max(0.0, float(cmd.get("t", 0)))
                except (TypeError, ValueError):
                    return
                if actual.get("dur"):
                    t = min(t, actual["dur"] - 1)
                if self.paused_pos is not None:
                    self.paused_pos = t
                else:
                    self.anchor = time.time() - t


@st.cache_resource
def get_party_room(version: int) -> PartyRoom:
    return PartyRoom()


room = get_party_room(ROOM_VERSION)


# =========================================================
# IDENTIDAD Y MODO ADMIN
# =========================================================
def obtener_id_invitado() -> str:
    gid = st.query_params.get("g", "")
    if not re.fullmatch(r"[0-9a-f]{12}", gid or ""):
        gid = uuid.uuid4().hex[:12]
        st.query_params["g"] = gid
    return gid


def pin_valido(pin: str) -> bool:
    return bool(pin) and hmac.compare_digest(str(pin), HOST_PIN)


GUEST_ID = obtener_id_invitado()
ES_HOST = pin_valido(st.query_params.get("host", ""))
AUTO_AUDIO = ES_HOST and st.query_params.get("audio", "1") != "0"


# =========================================================
# YOUTUBE MUSIC
# =========================================================
@st.cache_resource
def get_ytmusic():
    try:
        return YTMusic()
    except Exception:
        return None


def mejor_miniatura(thumbnails: list[dict]) -> str:
    if not thumbnails:
        return ""
    return re.sub(r"=w\d+-h\d+", "=w400-h400", thumbnails[-1].get("url", ""))


def a_segundos(item: dict) -> int:
    seg = item.get("duration_seconds")
    if isinstance(seg, (int, float)) and seg > 0:
        return int(seg)
    total = 0
    try:
        for parte in (item.get("duration") or "").split(":"):
            total = total * 60 + int(parte)
    except ValueError:
        return 0
    return total


# ---------- Texto: normalización y detección de versiones ----------
def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_artista(nombre: str) -> str:
    a = normalizar(nombre)
    a = re.sub(r"\b(vevo|topic|official|oficial|music)\b", " ", a)
    a = re.sub(r"vevo$", "", a.replace(" ", ""))
    return a


# Palabras que indican "otra versión" del tema. Solo restan puntos
# si NO aparecen en lo que buscó la persona.
VERSION_FUERTE = {
    "remix", "rmx", "cover", "live", "en vivo", "en directo", "acoustic", "acustico",
    "karaoke", "instrumental", "sped up", "speed up", "slowed", "reverb", "nightcore",
    "8d", "bass boosted", "mashup", "bootleg", "flip", "tribute", "tributo", "extended",
    "vip", "lofi", "lo fi", "parodia", "parody", "reaction", "reaccion", "tutorial",
}
VERSION_SUAVE = {"edit", "version", "mix", "mixed", "rework", "dub"}
PALABRAS_VERSION = sorted(VERSION_FUERTE | VERSION_SUAVE, key=len, reverse=True)

_RE_RUIDO = re.compile(
    r"[\(\[][^\)\]]*\b(official|oficial|video|audio|lyrics?|letra|visuali[sz]er|hd|hq|4k|"
    r"explicit|clean|remaster(ed)?|feat|ft|con)\b[^\)\]]*[\)\]]",
    re.I,
)


def etiquetas_version(texto_norm: str) -> set[str]:
    return {p for p in PALABRAS_VERSION
            if re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", texto_norm)}


def titulo_base(titulo: str, artistas: list[str]) -> str:
    """'Skrillex - Bangarang feat. Sirah (Official Video)' → 'bangarang'."""
    t = _RE_RUIDO.sub(" ", titulo or "")
    partes = re.split(r"\s[-–—]\s", t, maxsplit=1)
    if len(partes) == 2:
        izq = normalizar_artista(partes[0])
        arts = [normalizar_artista(a) for a in artistas if a]
        if any(a and (a in izq or izq in a) for a in arts):
            t = partes[1]
    t = re.split(r"\b(?:feat|ft|featuring)\b\.?", t, maxsplit=1, flags=re.I)[0]
    return normalizar(t)


def a_numero(valor) -> float:
    """'1.2B' → 1.2e9 · '345M' → 3.45e8 (reproducciones/visitas)."""
    if isinstance(valor, (int, float)):
        return float(valor)
    m = re.match(r"\s*([\d.,]+)\s*([KMB])?", str(valor or ""), re.I)
    if not m:
        return 0.0
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return 0.0
    return num * {"K": 1e3, "M": 1e6, "B": 1e9}.get((m.group(2) or "").upper(), 1)


# ---------- ¿Se puede reproducir incrustado en un celular? ----------
# Muchos videos (sobre todo los "Topic"/audio de sellos grandes) bloquean la
# reproducción fuera de YouTube. Se comprueba en el servidor ANTES de
# ofrecerlos, para que ningún dispositivo (admin o invitado) se tope con ellos.
@st.cache_resource
def _memoria() -> dict:
    """Vive mientras la app esté encendida (las variables normales del script
    se reinician en cada recarga de Streamlit)."""
    return {"lock": threading.Lock(), "embed": {}, "malos_movil": {}, "buenos_movil": {}}


MEM = _memoria()  # se usa también desde hilos en segundo plano


def malos_en_movil() -> set[str]:
    """Videos que algún celular ya reportó como bloqueados (error 101/150)."""
    mem, limite = MEM, time.time() - 24 * 3600
    with mem["lock"]:
        return {v for v, t in mem["malos_movil"].items() if t > limite}


def buenos_en_movil() -> set[str]:
    """Videos que un celular ya reprodujo bien (comprobado en el propio teléfono)."""
    mem, limite = MEM, time.time() - 24 * 3600
    with mem["lock"]:
        return {v for v, t in mem["buenos_movil"].items() if t > limite}


def registrar_buenos(vids, movil: bool):
    with MEM["lock"]:
        for vid in list(vids or [])[:60]:
            if not isinstance(vid, str) or not re.fullmatch(r"[\w-]{11}", vid):
                continue
            MEM["embed"][vid] = (time.time(), True)
            if movil:
                MEM["buenos_movil"][vid] = time.time()
                MEM["malos_movil"].pop(vid, None)


def registrar_fallos(fallos: dict, movil: bool):
    mem = MEM
    with mem["lock"]:
        for vid, codigo in list(fallos.items())[:60]:
            if not isinstance(vid, str) or not re.fullmatch(r"[\w-]{11}", vid):
                continue
            try:
                codigo = int(codigo)
            except (TypeError, ValueError):
                continue
            if codigo in (100, 101, 150):
                if movil:
                    mem["malos_movil"][vid] = time.time()
                    mem["buenos_movil"].pop(vid, None)
                else:
                    mem["embed"][vid] = (time.time(), False)


_UA_ANDROID = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36")
_EMBED_CLIENT_VERSION = "1.20250310.01.00"


def _consultar_embed(vid: str) -> bool | None:
    """True = se puede incrustar · False = bloqueado · None = no se sabe."""
    # 1) oEmbed: responde 401/403 si el dueño desactivó la inserción
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"},
            headers={"User-Agent": _UA_ANDROID}, timeout=4,
        )
        if r.status_code in (401, 403, 404):
            return False
    except requests.RequestException:
        pass

    # 2) Mismo cliente que usa el reproductor incrustado en un teléfono
    try:
        r = requests.post(
            "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
            json={
                "videoId": vid,
                "context": {
                    "client": {
                        "clientName": "WEB_EMBEDDED_PLAYER",
                        "clientVersion": _EMBED_CLIENT_VERSION,
                        "hl": "en", "gl": "CL",
                        "platform": "MOBILE", "clientFormFactor": "SMALL_FORM_FACTOR",
                        "osName": "Android", "osVersion": "14", "userAgent": _UA_ANDROID,
                    },
                    "thirdParty": {"embedUrl": APP_URL},
                },
                "racyCheckOk": False,
                "contentCheckOk": False,
            },
            headers={
                "User-Agent": _UA_ANDROID,
                "Origin": "https://www.youtube.com",
                "X-YouTube-Client-Name": "56",
                "X-YouTube-Client-Version": _EMBED_CLIENT_VERSION,
            },
            timeout=5,
        )
        if not r.ok:
            return None
        ps = r.json().get("playabilityStatus") or {}
        estado = ps.get("status")
        razon = json.dumps(ps, ensure_ascii=False).lower()
        if estado == "OK":
            return ps.get("playableInEmbed", True) is not False
        if "country" in razon or "pais" in razon or "país" in razon:
            return None  # bloqueo por región del SERVIDOR: en Chile puede funcionar
        if "bot" in razon:
            return None  # YouTube pidió verificación al servidor: no concluyente
        if estado in ("UNPLAYABLE", "ERROR"):
            return False
        if estado in ("LOGIN_REQUIRED", "AGE_CHECK_REQUIRED", "CONTENT_CHECK_REQUIRED"):
            if any(p in razon for p in ("age", "edad", "inappropriate", "inapropiado")):
                return False  # +18: nunca se reproduce incrustado
            return None
    except Exception:  # noqa: BLE001
        pass
    return None


def verificar_lote(vids: list[str]) -> dict[str, bool | None]:
    """Comprueba varios videos en paralelo (con caché en memoria)."""
    mem = MEM
    ahora, resultado, faltan = time.time(), {}, []
    with mem["lock"]:
        for v in dict.fromkeys(vids):
            hit = mem["embed"].get(v)
            if hit and ahora - hit[0] < EMBED_TTL:
                resultado[v] = hit[1]
            else:
                faltan.append(v)
    if faltan:
        with cf.ThreadPoolExecutor(max_workers=min(12, len(faltan))) as ex:
            for v, ok in zip(faltan, ex.map(_consultar_embed, faltan)):
                resultado[v] = ok
        with mem["lock"]:
            for v in faltan:
                if resultado[v] is not None:  # lo desconocido se vuelve a intentar
                    mem["embed"][v] = (ahora, resultado[v])
    return resultado


# ---------- Búsqueda con ranking por popularidad ----------
def _a_candidato(item: dict, filtro: str | None) -> dict | None:
    vid = item.get("videoId")
    tipo = item.get("resultType") or ("song" if filtro == "songs" else "video")
    if not vid or tipo not in ("song", "video"):
        return None
    lista_artistas = [a["name"] for a in (item.get("artists") or []) if a.get("name")]
    titulo = item.get("title") or "Canción desconocida"
    return {
        "video_id": vid,
        "title": titulo,
        "artist": ", ".join(lista_artistas) or item.get("author") or "Artista desconocido",
        "artistas": lista_artistas,
        "duration": item.get("duration") or "",
        "dur": a_segundos(item),
        "thumbnail": mejor_miniatura(item.get("thumbnails") or []),
        "tipo": tipo,
        "views": a_numero(item.get("views") or item.get("plays")),
        "bonus": 0.0,
    }


def _puntuar(c: dict, q_norm: str, q_tokens: list[str], q_versiones: set[str]) -> float:
    titulo = normalizar(c["title"])
    texto = f"{titulo} {normalizar(c['artist'])}"
    q_junto = q_norm.replace(" ", "")

    # ¿Cuántas palabras de la búsqueda aparecen en título + artista?
    cobertura = sum(1 for t in q_tokens if t in texto) / max(1, len(q_tokens))
    s = 45 * cobertura

    # El título "limpio" está contenido en lo que se buscó → coincidencia exacta
    base = c["base"]
    if base and base.replace(" ", "") in q_junto:
        s += 18
    # El artista está en la búsqueda
    if any(a and a in q_junto for a in (normalizar_artista(x) for x in c["artistas"] or [c["artist"]])):
        s += 15

    s += c["bonus"]  # posición que le dio YouTube Music (top result, etc.)
    s += min(30.0, 3.2 * math.log10(c["views"] + 1))  # popularidad

    # Remixes, covers, en vivo, sped up… solo si la persona los pidió
    for etiqueta in etiquetas_version(titulo) - q_versiones:
        s -= 38 if etiqueta in VERSION_FUERTE else 12
    if c["dur"] > 720 and not q_versiones:
        s -= 15  # mezclas de 1 hora, compilados…
    return s


def _misma_cancion(a: dict, b: dict) -> bool:
    if a["base"] != b["base"] or a["tags"] != b["tags"]:
        return False
    if a["dur"] and b["dur"] and abs(a["dur"] - b["dur"]) > max(30, a["dur"] * 0.15):
        return False
    arts_a = {normalizar_artista(x) for x in a["artistas"]} - {""}
    arts_b = {normalizar_artista(x) for x in b["artistas"]} - {""}
    if arts_a and arts_b and not (arts_a & arts_b):
        texto_b = normalizar(b["title"]).replace(" ", "")
        return any(x in texto_b for x in arts_a)
    return True


@st.cache_data(ttl=900, show_spinner=False)
def buscar_canciones(consulta: str):
    yt = get_ytmusic()
    if yt is None:
        return None

    q_norm = normalizar(consulta)
    q_tokens = [t for t in q_norm.split() if len(t) > 1] or q_norm.split()
    q_versiones = etiquetas_version(q_norm)

    candidatos: dict[str, dict] = {}

    def sumar(item, filtro, bonus):
        c = _a_candidato(item, filtro)
        if not c:
            return
        previo = candidatos.get(c["video_id"])
        if previo:
            previo["bonus"] = max(previo["bonus"], bonus)
            previo["views"] = max(previo["views"], c["views"])
        else:
            c["bonus"] = bonus
            candidatos[c["video_id"]] = c

    # 1) Búsqueda general: el "Resultado principal" suele ser el tema original y popular
    try:
        for i, item in enumerate(yt.search(consulta, limit=20) or []):
            es_top = (item.get("category") or "").lower() in ("top result", "resultado principal")
            sumar(item, None, 40 if es_top else max(0, 10 - i))
    except Exception:  # noqa: BLE001
        pass
    # 2) Canciones, 3) videos y 4) videos con letra (respaldo para celulares)
    for filtro, q, base_bonus, paso in (("songs", consulta, 22, 2.0), ("videos", consulta, 16, 1.5),
                                        ("videos", f"{consulta} letra", 0, 0)):
        try:
            crudos = yt.search(q, filter=filtro, limit=MAX_RESULTADOS * 2) or []
        except Exception:  # noqa: BLE001
            crudos = []
        for i, item in enumerate(crudos):
            sumar(item, filtro, max(0.0, base_bonus - paso * i))

    if not candidatos:
        return []

    for c in candidatos.values():
        c["base"] = titulo_base(c["title"], c["artistas"])
        c["tags"] = frozenset(etiquetas_version(normalizar(c["title"])))
        c["score"] = _puntuar(c, q_norm, q_tokens, q_versiones)

    # Agrupa versiones del mismo tema (audio, video oficial, lyric…) en una sola fila
    grupos: list[list[dict]] = []
    for c in sorted(candidatos.values(), key=lambda x: x["score"], reverse=True):
        for g in grupos:
            if _misma_cancion(g[0], c):
                g.append(c)
                break
        else:
            grupos.append([c])

    # Comprueba qué versiones se pueden reproducir en cualquier dispositivo
    revisar = grupos[:MAX_VERIFICAR]
    estado = verificar_lote([c["video_id"] for g in revisar for c in g[:6]])

    def armar(g, elegido):
        rep = g[0]
        otros = [c["video_id"] for c in g[:6]
                 if c is not elegido and estado.get(c["video_id"]) is not False]
        return {
            "video_id": elegido["video_id"],
            "title": rep["title"],
            "artist": rep["artist"],
            "duration": elegido["duration"] or rep["duration"],
            "dur": elegido["dur"] or rep["dur"],
            "thumbnail": rep["thumbnail"] or elegido["thumbnail"],
            "cands": otros,
        }

    resultados = []
    for g in revisar:
        malos = malos_en_movil()
        jugables = sorted((c for c in g[:6] if estado.get(c["video_id"]) is True),
                          key=lambda c: c["video_id"] in malos)
        dudosos = [c for c in g[:6] if estado.get(c["video_id"]) is None]
        elegido = (jugables or dudosos or [None])[0]
        if elegido:
            resultados.append(armar(g, elegido))
        if len(resultados) >= MAX_RESULTADOS:
            break

    # Si YouTube bloqueó todas las comprobaciones, mejor mostrar algo que nada
    if not resultados:
        resultados = [armar(g, g[0]) for g in grupos[:MAX_RESULTADOS]]
    return resultados


def _versiones(yt, titulo: str, artista: str, video_id: str, dur: int,
               amplio: bool = False, excluir=()) -> list[str]:
    """Otras subidas del MISMO tema (video oficial, lyric video, audio…),
    descartando remixes/covers, otros artistas y duraciones muy distintas.
    amplio=True busca más lejos (letra/lyrics/audio de canales no oficiales,
    que casi nunca bloquean la reproducción en celulares)."""
    if yt is None:
        return []
    artistas = [a.strip() for a in artista.split(",") if a.strip() and a != "Artista desconocido"]
    base = titulo_base(titulo, artistas)
    if not base:
        return []
    tags_orig = etiquetas_version(normalizar(titulo))
    principal = normalizar_artista(artistas[0]) if artistas else ""
    consulta = f"{artistas[0] if artistas else ''} {base}".strip()

    if amplio:
        busquedas = (("videos", f"{consulta} letra", 20), ("videos", f"{consulta} lyrics", 20),
                     ("videos", f"{consulta} audio", 20), ("videos", f"{base} {consulta}", 20),
                     (None, f"{consulta} letra", 15))
        tolerancia = lambda d: max(40, d * 0.2)  # noqa: E731
    else:
        busquedas = (("videos", consulta, 10), ("songs", consulta, 10), (None, consulta, 10),
                     ("videos", f"{consulta} lyrics", 10))
        tolerancia = lambda d: max(25, d * 0.12)  # noqa: E731

    vistos, salida = {video_id, *excluir}, []
    for filtro, q, limite in busquedas:
        try:
            crudos = (yt.search(q, filter=filtro, limit=limite) if filtro
                      else yt.search(q, limit=limite)) or []
        except Exception:  # noqa: BLE001
            crudos = []
        for item in crudos:
            c = _a_candidato(item, filtro)
            if not c or c["video_id"] in vistos:
                continue
            vistos.add(c["video_id"])
            t_norm = normalizar(c["title"])
            if etiquetas_version(t_norm) - tags_orig:
                continue  # es un remix/cover/en vivo: otra canción
            if not all(p in t_norm for p in base.split()):
                continue
            if principal:
                texto = (t_norm + " " + normalizar(c["artist"])).replace(" ", "")
                if principal not in texto:
                    continue  # mismo nombre, otro artista
            if dur and c["dur"] and abs(c["dur"] - dur) > tolerancia(dur):
                continue
            oficial = bool(re.search(r"\b(official|oficial)\b", t_norm)) or "vevo" in c["artist"].lower()
            salida.append((oficial if amplio else False, c["video_id"]))
    # En modo amplio, primero las subidas no oficiales (las más permisivas)
    salida.sort(key=lambda x: x[0])
    return [v for _, v in salida][:12]


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_versiones(titulo: str, artista: str, video_id: str, dur: int) -> list[str]:
    return _versiones(get_ytmusic(), titulo, artista, video_id, dur)


def ordenar_por_confianza(vids: list[str]) -> list[str]:
    estado, malos, probados = verificar_lote(vids), malos_en_movil(), buenos_en_movil()
    vids = sorted(vids, key=lambda v: v not in probados)  # primero las probadas en celular
    buenos = [v for v in vids if estado.get(v) is True and v not in malos]
    dudosos = [v for v in vids if estado.get(v) is None and v not in malos]
    reportados = [v for v in vids if v in malos and estado.get(v) is not False]
    return buenos + dudosos + reportados


def preparar_alternativas(resultado: dict) -> list[str]:
    principal = resultado["video_id"]
    vids = [v for v in resultado.get("cands", []) if v != principal]
    for v in buscar_versiones(resultado["title"], resultado["artist"], principal,
                              int(resultado.get("dur") or 0)):
        if v not in vids and v != principal:
            vids.append(v)
    return ordenar_por_confianza(vids)[:MAX_ALTERNATIVAS]


def ampliar_alternativas(yt, cancion: dict, ya_probados: list[str]):
    """Corre en segundo plano cuando un dispositivo agotó todas las versiones."""
    nuevos: list[str] = []
    try:
        excluir = {*ya_probados, *cancion.get("alts", [])}
        candidatos = _versiones(yt, cancion["title"], cancion["artist"], cancion["video_id"],
                                int(cancion.get("dur") or 0), amplio=True, excluir=excluir)
        nuevos = [v for v in ordenar_por_confianza(candidatos) if v not in malos_en_movil()][:8]
    except Exception:  # noqa: BLE001
        pass
    finally:
        room.sumar_alternativas(cancion["uid"], nuevos)


# =========================================================
# CALLBACKS
# =========================================================
def on_agregar(resultado: dict, invitado: str, es_host: bool):
    try:
        alts = preparar_alternativas(resultado)
    except Exception:  # noqa: BLE001
        alts = list(resultado.get("cands", []))[:MAX_ALTERNATIVAS]
    cancion = {
        **{k: v for k, v in resultado.items() if k != "cands"},
        "alts": alts,
        "uid": uuid.uuid4().hex,
        "color": random.choice(COLORES),
        "added_by": invitado,
        "added_at": time.time(),
    }
    ok, mensaje = room.agregar(cancion, invitado, es_host)
    st.session_state.flash = ("ok" if ok else "warn", mensaje)
    if ok and not es_host:
        st.session_state.current_query = ""


def on_cerrar_resultados():
    st.session_state.current_query = ""
    st.session_state.search_input = ""  # también limpia la barra de búsqueda


def on_limpiar_confirmado():
    room.limpiar()
    st.session_state.confirmar_limpiar = False


def on_cmd(es_host: bool):
    """Recibe órdenes del reproductor a través de un campo oculto."""
    try:
        cmd = json.loads(st.session_state.get("mn_cmd") or "")
    except ValueError:
        return
    if not isinstance(cmd, dict):
        return
    c = cmd.get("c")
    if c == "probe":
        movil = bool(cmd.get("m"))
        registrar_buenos(cmd.get("ok") if isinstance(cmd.get("ok"), list) else [], movil)
        registrar_fallos(cmd.get("bad") if isinstance(cmd.get("bad"), dict) else {}, movil)
        return
    if c in ("more", "fail"):
        fallos = cmd.get("fails") if isinstance(cmd.get("fails"), dict) else {}
        registrar_fallos(fallos, bool(cmd.get("m")))
        if c == "more":
            cancion = room.pedir_mas_versiones(str(cmd.get("tok", "")))
            if cancion:
                probados = [v for v in (cmd.get("tried") or []) if isinstance(v, str)][:20]
                threading.Thread(target=ampliar_alternativas,
                                 args=(get_ytmusic(), cancion, probados), daemon=True).start()
        return
    room.comando(cmd, es_host)


def estado_codificado() -> str:
    e = room.estado()
    malos = malos_en_movil()
    buenos = buenos_en_movil()
    e["bad"] = [v for v in [e["vid"], *e["alts"]] if v and v in malos]
    e["good"] = [v for v in [e["vid"], *e["alts"]] if v and v in buenos]
    return base64.b64encode(json.dumps(e, ensure_ascii=False).encode()).decode()


# =========================================================
# ESTILOS
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ---------- Base ---------- */
.stApp {
    background:
        radial-gradient(900px 420px at 50% -140px, rgba(255, 34, 34, 0.18), transparent 70%),
        #0b0b0d;
    color: #f5f5f7;
    font-family: 'Inter', system-ui, sans-serif;
}
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebarCollapsedControl"], footer { display: none !important; }
.block-container { max-width: 600px !important; padding: 2.4rem 1.1rem 3rem !important; }
[data-testid="InputInstructions"], [data-testid="stInputInstructions"] { display: none !important; }

/* ---------- Encabezado ---------- */
h1.mn-title, .mn-title {
    text-align: center !important; margin: 0 !important; padding: 0 !important; line-height: 1 !important;
    font-family: 'Inter', system-ui, sans-serif !important; color: #ff2222 !important;
    font-size: clamp(2.6rem, 9vw, 3.4rem); font-weight: 900; letter-spacing: -0.055em;
    text-shadow: 0 0 32px rgba(255, 34, 34, 0.35);
}
h1.mn-title a, [data-testid="stHeaderActionElements"] { display: none !important; }
.mn-sub {
    text-align: center; margin: 0.55rem 0 0.2rem; font-size: 0.95rem; font-weight: 700;
    background: linear-gradient(90deg, #ff2222 0%, #ff2222 20%, #ff6b00 32%, #00f0ff 42%, #a855f7 52%, #ec4899 62%, #ff2222 75%, #ff2222 100%);
    background-size: 260% 100%;
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    animation: rgbWave 3.8s ease-in-out infinite alternate;
}
@keyframes rgbWave { from { background-position: 100% 0; } to { background-position: 0 0; } }

.mn-section {
    display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
    margin: 1.8rem 0 0.4rem; padding: 0 4px;
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: #7a7a85;
}
.mn-section em { font-style: normal; color: #b5b5bf; letter-spacing: 0; text-transform: none; font-size: 0.78rem;
                 white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mn-empty { text-align: center; color: #6f6f7a; font-size: 0.85rem; padding: 18px 0 6px; }
.mn-hint  { text-align: center; color: #8a8a95; font-size: 0.8rem; margin: 0.3rem 0 0.4rem; }

/* ---------- Canal oculto Python ↔ reproductor ---------- */
.st-key-mn_state, .st-key-mn_cmd { display: none !important; }

/* ---------- Buscador ---------- */
.st-key-search_box { margin-top: -0.9rem; }
.st-key-search_box [data-testid="stForm"] {
    background: #141418 !important; border: 1.5px solid rgba(255, 34, 34, 0.55) !important;
    border-radius: 999px !important; padding: 4px 5px 4px 16px !important;
    box-shadow: 0 0 18px rgba(255, 34, 34, 0.16) !important; transition: all 0.25s ease !important;
}
.st-key-search_box [data-testid="stForm"]:focus-within {
    border-color: #ff4040 !important; box-shadow: 0 0 26px rgba(255, 34, 34, 0.38) !important;
}
.st-key-search_box [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.4rem !important; }
.st-key-search_box [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-search_box [data-testid="stColumn"]:nth-child(1) { flex: 1 1 auto !important; }
.st-key-search_box [data-testid="stColumn"]:nth-child(2) { flex: 0 0 96px !important; }
.st-key-search_box [data-testid="stTextInput"] > div > div { background: transparent !important; border: none !important; box-shadow: none !important; }
.st-key-search_box input { background: transparent !important; color: #fff !important; font-size: 0.95rem !important; }
.st-key-search_box button {
    border-radius: 999px !important; background: #ff2222 !important; border: none !important;
    color: #fff !important; font-weight: 700 !important; box-shadow: 0 0 12px rgba(255, 34, 34, 0.35) !important;
}
.st-key-search_box button:hover { background: #ff4545 !important; box-shadow: 0 0 18px rgba(255, 34, 34, 0.6) !important; }

/* ---------- Mini scroll de resultados ---------- */
.st-key-results_scroll {
    background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 16px; padding: 4px 2px 10px 0 !important;
    overflow-y: auto; scrollbar-width: thin; scrollbar-color: rgba(255, 34, 34, 0.6) transparent;
}
.st-key-results_scroll::-webkit-scrollbar, .st-key-results_scroll *::-webkit-scrollbar { width: 6px; }
.st-key-results_scroll::-webkit-scrollbar-track, .st-key-results_scroll *::-webkit-scrollbar-track { background: transparent; }
.st-key-results_scroll::-webkit-scrollbar-thumb, .st-key-results_scroll *::-webkit-scrollbar-thumb {
    background: rgba(255, 34, 34, 0.55); border-radius: 999px;
}
.st-key-results_scroll::-webkit-scrollbar-thumb:hover, .st-key-results_scroll *::-webkit-scrollbar-thumb:hover { background: #ff2222; }

/* ---------- Botones fantasma ---------- */
.stButton button, div[data-testid="stPopover"] > div > button {
    background: transparent !important; color: #c9c9d1 !important; border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 999px !important; font-size: 0.82rem; font-weight: 500; transition: all 0.2s ease;
}
.stButton button:hover:enabled, div[data-testid="stPopover"] > div > button:hover {
    background: #ff2222 !important; border-color: #ff2222 !important; color: #fff !important;
    box-shadow: 0 0 14px rgba(255, 34, 34, 0.45);
}
.stButton button:disabled { opacity: 0.4; }

/* ---------- Filas (resultados y cola) ---------- */
[class*="st-key-li-"] { padding: 6px 8px; border-radius: 14px; transition: background 0.2s ease; margin-bottom: -0.55rem; }
[class*="st-key-li-"]:hover { background: rgba(255, 255, 255, 0.04); }
[class*="st-key-li-"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.7rem !important; align-items: center !important; }
[class*="st-key-li-"] [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
[class*="st-key-li-"] [data-testid="stColumn"]:nth-child(1) { flex: 0 0 44px !important; overflow: hidden; }
[class*="st-key-li-"] [data-testid="stColumn"]:nth-child(2) { flex: 1 1 auto !important; }
[class*="st-key-li-"] [data-testid="stColumn"]:nth-child(n+3) { flex: 0 0 34px !important; }
[class*="st-key-li-"] [data-testid="stElementToolbar"] { display: none !important; }
[class*="st-key-li-"] img { width: 44px !important; height: 44px !important; border-radius: 9px; object-fit: cover; }
[class*="st-key-li-"] .stButton button {
    width: 34px !important; min-width: 34px !important; height: 34px !important; min-height: 34px !important;
    padding: 0 !important; border-radius: 50% !important; display: flex; align-items: center; justify-content: center;
}
[class*="st-key-li-"] .stButton button span[data-testid="stIconMaterial"] { font-size: 1.1rem; }
.li-t { font-size: 0.88rem; font-weight: 600; color: #f2f2f5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.li-a { font-size: 0.76rem; color: #8a8a95; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; }
.li-n { color: #ff4d4d; font-weight: 700; margin-right: 6px; font-variant-numeric: tabular-nums; }
.li-me { color: #ff8080; }

[data-testid="stExpander"] details { border: none !important; background: transparent !important; }
[data-testid="stExpander"] summary { color: #7a7a85; font-size: 0.8rem; padding-left: 4px; }

.st-key-host_area { align-items: center; margin-top: 0.8rem; }
.st-key-tools_row [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; justify-content: center; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# REPRODUCTOR SINCRONIZADO (iframe persistente)
# =========================================================
PLAYER_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root { --accent: #ff2222; --muted: #8a8a95; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: transparent; }
  body {
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; color: #f5f5f7;
    display: flex; justify-content: center; padding: 6px 10px 0;
    -webkit-font-smoothing: antialiased; user-select: none; overflow: hidden;
  }
  .wrap { width: 100%; max-width: 440px; display: flex; flex-direction: column; align-items: center; text-align: center; }

  /* Vinilo */
  .stage { position: relative; width: 210px; height: 210px; margin: 22px 0 24px; flex-shrink: 0; }
  .glow {
    position: absolute; inset: -34px; border-radius: 50%; pointer-events: none;
    background: radial-gradient(circle, var(--accent) 0%, transparent 66%);
    filter: blur(30px); opacity: 0.22; transition: background 0.8s ease, opacity 0.8s ease;
  }
  .spinning:not(.paused) .glow { animation: breathe 3.2s ease-in-out infinite; }
  @keyframes breathe { 50% { opacity: 0.48; transform: scale(1.07); } }
  .vinyl {
    position: relative; width: 210px; height: 210px; border-radius: 50%; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    background:
      radial-gradient(circle at center, transparent 39%, rgba(0,0,0,0.85) 40%, transparent 41%),
      repeating-radial-gradient(circle at center, #0d0d0d 0px, #0d0d0d 2px, #1f1f1f 3px, #121212 4px),
      conic-gradient(from 45deg, #050505, #353535 22deg, #050505 45deg, #050505 225deg, #353535 247deg, #050505 270deg);
    box-shadow: 0 14px 34px rgba(0,0,0,0.75), 0 0 0 1px rgba(255,255,255,0.04), 0 0 22px var(--accent);
    transition: box-shadow 0.8s ease;
  }
  .stage::after {
    content: ''; position: absolute; inset: 0; border-radius: 50%; pointer-events: none;
    background: conic-gradient(from 20deg, transparent 0deg 40deg, rgba(255,255,255,0.07) 62deg, transparent 84deg 220deg,
                rgba(255,255,255,0.05) 242deg, transparent 264deg);
  }
  .label {
    width: 86px; height: 86px; border-radius: 50%;
    background: var(--accent) center / cover no-repeat;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 0 3px rgba(0,0,0,0.55), 0 0 14px var(--accent);
    transition: box-shadow 0.8s ease;
  }
  .hole { width: 10px; height: 10px; border-radius: 50%; background: #e9e9ee; box-shadow: inset 0 0 2px rgba(0,0,0,0.8); }
  .spinning .vinyl { animation: spin 2.4s linear infinite; }
  .paused .vinyl { animation-play-state: paused; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty .vinyl { opacity: 0.55; box-shadow: 0 14px 34px rgba(0,0,0,0.75); }
  .empty .label { background-image: none !important; background-color: #2a2a30; box-shadow: 0 0 0 3px rgba(0,0,0,0.55); }

  .unlock {
    position: absolute; inset: 0; z-index: 3; border-radius: 50%; border: 2px solid var(--accent);
    background: rgba(8,8,10,0.82); color: #fff; font-family: inherit; font-size: 0.86rem; font-weight: 700;
    cursor: pointer; display: none; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  }
  .unlock.show { display: flex; animation: pulse 1.4s ease-in-out infinite; }
  .unlock svg { width: 30px; height: 30px; fill: currentColor; }
  @keyframes pulse { 50% { box-shadow: 0 0 28px var(--accent); } }

  /* Texto */
  .eyebrow { font-size: 0.66rem; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent); transition: color 0.8s; }
  .title { margin-top: 7px; font-size: 1.2rem; font-weight: 800; letter-spacing: -0.015em; max-width: 100%;
           white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .artist { margin-top: 3px; font-size: 0.88rem; color: var(--muted); max-width: 100%;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* Progreso */
  .progress { width: 100%; display: flex; align-items: center; gap: 10px; margin-top: 18px; }
  .time { font-size: 0.72rem; color: var(--muted); min-width: 34px; font-variant-numeric: tabular-nums; }
  .time:first-child { text-align: right; }
  input[type=range] { -webkit-appearance: none; appearance: none; height: 4px; border-radius: 4px; background: #2c2c33; outline: none; cursor: pointer; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; border-radius: 50%; background: #fff; box-shadow: 0 0 8px var(--accent); }
  input[type=range]::-moz-range-thumb { width: 12px; height: 12px; border: none; border-radius: 50%; background: #fff; }
  #progress { flex: 1; }
  .wrap:not(.host) #progress { pointer-events: none; cursor: default; }
  .wrap:not(.host) #progress::-webkit-slider-thumb { width: 0; height: 0; box-shadow: none; }
  .wrap:not(.host) #progress::-moz-range-thumb { width: 0; height: 0; }

  /* Controles (solo admin) */
  .controls { display: flex; align-items: center; justify-content: center; gap: 22px; margin-top: 14px; }
  .icon-btn { width: 44px; height: 44px; border-radius: 50%; border: none; background: transparent; color: #d4d4db;
              display: grid; place-items: center; cursor: pointer; transition: all 0.2s ease; }
  .icon-btn svg { width: 22px; height: 22px; fill: currentColor; }
  .icon-btn:hover:enabled { color: #fff; background: rgba(255,255,255,0.07); }
  .icon-btn:disabled { opacity: 0.25; cursor: default; }
  .play-btn { width: 60px; height: 60px; background: var(--accent); color: #fff; box-shadow: 0 0 22px var(--accent); }
  .play-btn svg { width: 26px; height: 26px; }
  .play-btn:hover:enabled { background: var(--accent); transform: scale(1.06); }

  /* Escuchar aquí + volumen (todos) */
  .listen-row { display: flex; align-items: center; justify-content: center; gap: 14px; margin-top: 16px; flex-wrap: wrap; }
  .pill {
    display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 999px; cursor: pointer;
    font-family: inherit; font-size: 0.8rem; font-weight: 600; color: #e9e9ee;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.14); transition: all 0.2s ease;
  }
  .pill:hover { border-color: var(--accent); }
  .listening .pill { background: var(--accent); border-color: var(--accent); box-shadow: 0 0 16px var(--accent); color: #fff; }
  .pill svg { width: 16px; height: 16px; fill: currentColor; }
  .eq { display: none; gap: 2px; height: 11px; align-items: flex-end; }
  .listening:not(.paused) .eq { display: inline-flex; }
  .eq i { width: 3px; background: #fff; border-radius: 2px; animation: eq 0.9s ease-in-out infinite; }
  .eq i:nth-child(2) { animation-delay: 0.2s; } .eq i:nth-child(3) { animation-delay: 0.4s; }
  @keyframes eq { 0%, 100% { height: 3px; } 50% { height: 11px; } }
  .volume { display: flex; align-items: center; gap: 8px; color: var(--muted); }
  .volume svg { width: 16px; height: 16px; fill: currentColor; }
  #volume { width: 110px; }
  .wrap:not(.listening) .volume { display: none; }

  .upnext { margin-top: 16px; font-size: 0.76rem; color: #6f6f7a; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .upnext b { color: #b5b5bf; font-weight: 600; }
  .notice { margin-top: 8px; font-size: 0.76rem; color: #ffb020; min-height: 1em; }
  .open-yt {
    display: none; margin-top: 8px; padding: 7px 14px; border-radius: 999px; text-decoration: none;
    font-size: 0.76rem; font-weight: 600; color: #fff; background: #26262c; border: 1px solid rgba(255,255,255,0.14);
  }
  .open-yt.show { display: inline-flex; }

  .empty .progress, .empty .controls, .empty .listen-row, .empty .upnext { display: none !important; }
  .wrap:not(.host) .controls { display: none !important; }

  #yt { position: fixed; left: 0; top: 0; width: 200px; height: 200px; opacity: 0.01; pointer-events: none; z-index: -1; }
  #yt iframe { width: 200px; height: 200px; border: 0; }
</style>
</head>
<body>
<div id="yt"></div>

<div id="root" class="wrap empty">
  <div class="stage">
    <div class="glow"></div>
    <div id="vinyl" class="vinyl"><div id="label" class="label"><div class="hole"></div></div></div>
    <button id="unlock" class="unlock">
      <svg viewBox="0 0 24 24"><path d="M3 10v4h4l5 5V5L7 10H3zm13.5 2A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z"/></svg>
      Toca para escuchar
    </button>
  </div>

  <div id="eyebrow" class="eyebrow">MusicNow</div>
  <div id="title" class="title">Nada sonando todavía</div>
  <div id="artist" class="artist">Busca una canción y empieza la fiesta</div>

  <div class="progress">
    <span id="cur" class="time">0:00</span>
    <input id="progress" type="range" min="0" max="1000" value="0">
    <span id="dur" class="time">0:00</span>
  </div>

  <div class="controls">
    <button id="prev" class="icon-btn" title="Anterior"><svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zM9.5 12 18 18V6z"/></svg></button>
    <button id="play" class="icon-btn play-btn" title="Play / Pausa"><svg id="play-icon" viewBox="0 0 24 24"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg></button>
    <button id="next" class="icon-btn" title="Siguiente"><svg viewBox="0 0 24 24"><path d="M16 6h2v12h-2zM6 18l8.5-6L6 6z"/></svg></button>
  </div>

  <div class="listen-row">
    <button id="listen" class="pill">
      <svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 0 0-9 9v7a2 2 0 0 0 2 2h2v-8H5v-1a7 7 0 0 1 14 0v1h-2v8h2a2 2 0 0 0 2-2v-7a9 9 0 0 0-9-9z"/></svg>
      <span id="listen-text">Escuchar aquí</span>
      <span class="eq"><i></i><i></i><i></i></span>
    </button>
    <div class="volume">
      <svg viewBox="0 0 24 24"><path d="M3 10v4h4l5 5V5L7 10H3zm13.5 2A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4z"/></svg>
      <input id="volume" type="range" min="0" max="100" value="100">
    </div>
  </div>

  <div id="upnext" class="upnext">A continuación · <b id="upnext-title"></b></div>
  <div id="notice" class="notice"></div>
  <a id="open-yt" class="open-yt" href="#" target="_blank" rel="noopener">Abrir en YouTube ↗</a>
</div>

<script>
  const HOST = __HOST__, AUTO = __AUTO__;
  const P = window.parent.document;
  const $ = (id) => document.getElementById(id);
  const root = $('root');
  const ICON_PLAY = '<path d="M8 5v14l11-7z"/>';
  const ICON_PAUSE = '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/>';

  let S = null, rawPrev = '', offset = null;
  let player = null, ready = false, loadedToken = '', lastSeekAt = 0;
  let needTap = false, seeking = false, endedSent = '', watchdog = null;
  let curVid = '', tried = new Set(), gaveUp = false, noticeKind = '';
  let fails = {}, reported = false, waitingMore = false, askedMore = false, moreRev = 0, moreTimer = null;
  let softErrors = 0, rebuilt = false, recovering = false;
  const MOBILE = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '');
  let listening = AUTO;
  try { if (!AUTO && localStorage.getItem('mn_listen') === '1') listening = true; } catch (e) {}

  root.classList.toggle('host', HOST);
  root.classList.toggle('listening', listening);

  // ---------- Utilidades ----------
  function fit() {
    try {
      const f = window.frameElement;
      if (!f) return;
      const h = Math.ceil(root.getBoundingClientRect().bottom + 14);
      if (Math.abs(f.offsetHeight - h) > 2) { f.style.height = h + 'px'; f.setAttribute('height', h); }
      const box = f.closest('[data-testid="stElementContainer"]');
      if (box && Math.abs(box.offsetHeight - h) > 2) box.style.height = h + 'px';
    } catch (e) {}
  }
  window.addEventListener('resize', fit);

  const now = () => Date.now() / 1000;
  const serverNow = () => now() - (offset || 0);
  function targetPos(s) {
    if (!s || !s.token) return 0;
    let t = s.paused ? s.ppos : serverNow() - s.anchor;
    if (s.dur) t = Math.min(t, s.dur);
    return Math.max(0, t);
  }
  function fmt(sec) { sec = Math.floor(sec || 0); return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0'); }
  function paint(el, pct) { el.style.background = 'linear-gradient(to right, var(--accent) ' + pct + '%, #2c2c33 ' + pct + '%)'; }

  function decode(raw) {
    try {
      const bin = atob(raw);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return JSON.parse(new TextDecoder().decode(bytes));
    } catch (e) { return null; }
  }

  // Envía una orden a Python escribiendo en un campo oculto de Streamlit
  function sendCmd(cmd) {
    const input = P.querySelector('.st-key-mn_cmd input');
    if (!input) return;
    cmd.n = Math.random().toString(36).slice(2);
    const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
    setter.call(input, JSON.stringify(cmd));
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
  }

  // ---------- Estado de la sala ----------
  function poll() {
    const box = P.querySelector('.st-key-mn_state');
    if (!box) return;
    const m = (box.textContent || '').match(/[A-Za-z0-9+\/=]{16,}/);
    if (!m || m[0] === rawPrev) return;
    rawPrev = m[0];
    const s = decode(m[0]);
    if (!s) return;
    // Diferencia entre el reloj del servidor y el de este dispositivo
    const off = now() - s.now;
    offset = offset === null ? off : Math.min(off, offset + 0.02);
    S = s;
    applyUI();
    follow();
    checkMore();
  }

  function applyUI() {
    const s = S, has = !!s.token;
    document.documentElement.style.setProperty('--accent', s.color || '#ff2222');
    root.classList.toggle('empty', !has);
    root.classList.toggle('spinning', has);
    root.classList.toggle('paused', has && s.paused);
    $('eyebrow').textContent = has ? ((s.paused ? 'En pausa · ' : 'Sonando ahora · ') + s.pos + '/' + s.total) : 'MusicNow';
    $('title').textContent = has ? s.title : (s.total ? 'La lista terminó' : 'Nada sonando todavía');
    $('artist').textContent = has ? s.artist : 'Busca una canción y empieza la fiesta';
    $('label').style.backgroundImage = has && s.thumb ? 'url(' + JSON.stringify(s.thumb) + ')' : '';
    $('upnext').style.display = has && s.next ? '' : 'none';
    $('upnext-title').textContent = s.next || '';
    $('prev').disabled = !s.can_prev;
    $('next').disabled = !s.can_next;
    $('play-icon').innerHTML = s.paused ? ICON_PLAY : ICON_PAUSE;
    updateProgress();
    requestAnimationFrame(fit);
  }

  function updateProgress() {
    if (!S || !S.token || seeking) return;
    let dur = S.dur;
    if (!dur && ready && listening && player.getDuration) dur = player.getDuration();
    const pos = targetPos(S);
    $('cur').textContent = fmt(pos);
    $('dur').textContent = dur ? fmt(dur) : '--:--';
    const pct = dur ? Math.min(100, (pos / dur) * 100) : 0;
    $('progress').value = pct * 10;
    paint($('progress'), pct);
  }

  // ---------- Avisos ----------
  function setNotice(text, kind, showLink) {
    noticeKind = text ? (kind || 'info') : '';
    $('notice').textContent = text || '';
    $('open-yt').classList.toggle('show', !!showLink);
    requestAnimationFrame(fit);
  }
  $('open-yt').addEventListener('click', (e) => {
    if (!S || !S.vid) { e.preventDefault(); return; }
    // Abre la app/web de YouTube en el segundo exacto en que va la fiesta
    e.currentTarget.href = 'https://www.youtube.com/watch?v=' + encodeURIComponent(S.vid) +
                           '&t=' + Math.floor(targetPos(S)) + 's';
  });

  // ---------- Reproductor de YouTube (se carga en todos los dispositivos) ----------
  // Se crea el iframe a mano con origin + referrer: en celulares YouTube rechaza
  // (errores 101/150/152/153) los reproductores incrustados que no los envían.
  const ORIGIN = (() => {
    try { const o = window.parent.location.origin; if (o && o !== 'null') return o; } catch (e) {}
    try { if (location.origin && location.origin !== 'null') return location.origin; } catch (e) {}
    return '';
  })();

  // Errores que significan "ESTE video está bloqueado aquí". Cualquier otro
  // error (5, 2, 152, 153…) es un tropiezo del reproductor: se reintenta el
  // mismo video y, si sigue, se reinicia el reproductor. Nunca se busca otra
  // versión ni se salta la canción por esos errores.
  const BLOCKED = new Set([100, 101, 150]);

  function makeFrame() {
    const f = document.createElement('iframe');
    f.id = 'yt-player';
    f.width = '200'; f.height = '200';
    f.setAttribute('allow', 'autoplay; encrypted-media; picture-in-picture');
    f.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    f.setAttribute('title', 'Reproductor');
    f.src = 'https://www.youtube.com/embed/?enablejsapi=1&autoplay=1&controls=0&disablekb=1&fs=0&rel=0' +
            '&playsinline=1&iv_load_policy=3' + (ORIGIN ? '&origin=' + encodeURIComponent(ORIGIN) : '');
    $('yt').innerHTML = '';
    $('yt').appendChild(f);
  }

  function buildPlayer() {
    ready = false;
    try { if (player && player.destroy) player.destroy(); } catch (e) {}
    makeFrame();
    player = new YT.Player('yt-player', {
      events: {
        onReady: () => {
          ready = true;
          player.setVolume(+$('volume').value);
          // Si había una canción a medias, se vuelve a cargar en el reproductor nuevo
          if (loadedToken && S && S.token === loadedToken && curVid && listening) {
            player.loadVideoById({ videoId: curVid, startSeconds: targetPos(S) });
            lastSeekAt = now();
            armWatchdog();
          } else {
            follow();
          }
        },
        onStateChange: onState,
        onError: onError,
      },
    });
  }

  const tag = document.createElement('script');
  tag.src = 'https://www.youtube.com/iframe_api';
  document.head.appendChild(tag);
  window.onYouTubeIframeAPIReady = buildPlayer;

  // Mantiene este dispositivo alineado con el reloj del servidor
  function follow() {
    if (!player || !ready || !listening || !S) return;
    const s = S;
    if (!s.token) {
      if (loadedToken) { loadedToken = ''; player.stopVideo(); hideUnlock(); setNotice(''); }
      return;
    }
    const t = targetPos(s);
    if (s.token !== loadedToken) { startTrack(s, t); return; }
    if (needTap || gaveUp || waitingMore || recovering) return;
    const st = player.getPlayerState();
    if (s.paused) {
      if (st === 1 || st === 3) player.pauseVideo();
      return;
    }
    if (st === 0) return;  // terminó aquí; el servidor pasará a la siguiente
    if (st === 2 || st === 5 || st === -1) {
      player.seekTo(t, true);
      player.playVideo();
      lastSeekAt = now();
      armWatchdog();
      return;
    }
    if (st === 1 && now() - lastSeekAt > 4) {
      const drift = player.getCurrentTime() - t;
      if (Math.abs(drift) > 2.5 && !(s.dur && t >= s.dur - 1)) {
        player.seekTo(t, true);
        lastSeekAt = now();
      }
    }
  }

  // Orden de versiones a probar en ESTE dispositivo: primero las que ya se
  // sabe que funcionan aquí, al final las que se sabe que están bloqueadas.
  function candidates(s) {
    const all = [s.vid].concat(s.alts || []).filter((v, i, a) => v && a.indexOf(v) === i);
    const bad = new Set(MOBILE ? (s.bad || []) : []), good = new Set(MOBILE ? (s.good || []) : []);
    let local = {};
    try { local = JSON.parse(localStorage.getItem('mn_probe') || '{}'); } catch (e) {}
    const rank = (v) => (local[v] && local[v][0] === 1) || good.has(v) ? 0
                      : (local[v] && local[v][0] === 0) || bad.has(v) ? 2 : 1;
    return all.slice().sort((a, b) => rank(a) - rank(b));
  }

  function loadCandidate(vid) {
    curVid = vid;
    softErrors = 0;
    player.loadVideoById({ videoId: vid, startSeconds: targetPos(S) });
    lastSeekAt = now();
    armWatchdog();
  }

  // Carga una canción nueva
  function startTrack(s, t) {
    loadedToken = s.token;
    endedSent = '';
    tried = new Set();
    fails = {};
    reported = false;
    softErrors = 0;
    rebuilt = false;
    recovering = false;
    gaveUp = false;
    waitingMore = false;
    askedMore = false;
    clearTimeout(moreTimer);
    setNotice('');
    curVid = candidates(s)[0] || s.vid;
    player.loadVideoById({ videoId: curVid, startSeconds: t });
    lastSeekAt = now();
    armWatchdog();
  }

  function onState(e) {
    if (e.data === 1) {
      softErrors = 0;
      if (noticeKind === 'trying') setNotice('');
      if (!player.isMuted()) hideUnlock();
      try { localStorage.setItem('mn_probe', JSON.stringify(Object.assign(
        JSON.parse(localStorage.getItem('mn_probe') || '{}'), { [curVid]: [1, Date.now()] }))); } catch (err) {}
      // Si sonó gracias a otra versión, se avisa al servidor cuáles fallaron
      if (!reported && Object.keys(fails).length && S && S.token === loadedToken) {
        reported = true;
        sendCmd({ c: 'fail', tok: loadedToken, fails: fails, m: MOBILE });
      }
    }
    if (e.data === 0 && S && S.token === loadedToken && endedSent !== loadedToken) {
      endedSent = loadedToken;
      sendCmd({ c: 'ended', tok: loadedToken });
    }
  }

  function onError(e) {
    if (!loadedToken || !S || S.token !== loadedToken || gaveUp || waitingMore || recovering) return;
    if (endedSent === loadedToken) return;
    const code = e && e.data;
    const tok = loadedToken;

    // ---- Tropiezo del reproductor: reintentar el MISMO video ----
    if (!BLOCKED.has(code)) {
      recovering = true;
      // Mientras el verificador de resultados trabaja, los tropiezos no cuentan
      let probing = false;
      try { probing = !!window.parent.__mnProbing; } catch (err) {}
      if (!probing) softErrors++;
      if (probing || softErrors <= 3) {
        setTimeout(() => {
          recovering = false;
          if (S && S.token === tok && !gaveUp && ready) {
            player.loadVideoById({ videoId: curVid, startSeconds: targetPos(S) });
            lastSeekAt = now();
            armWatchdog();
          }
        }, probing ? 3000 : 1500 * softErrors);
      } else if (!rebuilt) {
        rebuilt = true;  // reproductor nuevo desde cero (una sola vez por canción)
        setNotice('Reconectando el reproductor…', 'trying');
        setTimeout(() => { recovering = false; softErrors = 0; buildPlayer(); }, 1000);
      } else {
        recovering = false;
        tried.add(curVid);  // tampoco funcionó así: se prueba otra versión
        fails[curVid] = code;
        if (!tryNext()) giveUp(code);
      }
      return;
    }

    // ---- Video bloqueado aquí: probar otra versión ----
    tried.add(curVid);
    fails[curVid] = code;
    try { localStorage.setItem('mn_probe', JSON.stringify(Object.assign(
      JSON.parse(localStorage.getItem('mn_probe') || '{}'), { [curVid]: [0, Date.now()] }))); } catch (err) {}
    if (tryNext()) return;
    if (!askedMore) { askMore(); return; }
    giveUp(code);
  }

  function tryNext() {
    const next = candidates(S).find((v) => !tried.has(v));
    if (!next) return false;
    setNotice('Cargando otra versión para este dispositivo…', 'trying');
    loadCandidate(next);
    return true;
  }

  // Se pide UNA sola vez por canción y con tiempo límite: nunca queda en bucle
  function askMore() {
    askedMore = true;
    waitingMore = true;
    moreRev = S.alts_rev || 0;
    setNotice('Buscando otra versión de la canción…', 'trying');
    sendCmd({ c: 'more', tok: loadedToken, tried: Array.from(tried), fails: fails, m: MOBILE });
    clearTimeout(moreTimer);
    moreTimer = setTimeout(() => {
      if (!waitingMore) return;
      waitingMore = false;
      if (!tryNext()) giveUp(150);
    }, 15000);
  }

  // Revisa si el servidor ya agregó versiones nuevas
  function checkMore() {
    if (!waitingMore || !S || S.token !== loadedToken) return;
    if (candidates(S).some((v) => !tried.has(v))) {
      waitingMore = false;
      clearTimeout(moreTimer);
      tryNext();
    } else if ((S.alts_rev || 0) > moreRev && !S.buscando) {
      waitingMore = false;  // terminó de buscar y no encontró nada nuevo
      clearTimeout(moreTimer);
      giveUp(150);
    }
  }

  function giveUp(code) {
    gaveUp = true;
    waitingMore = false;
    recovering = false;
    clearTimeout(moreTimer);
    hideUnlock();
    try { player.stopVideo(); } catch (e) {}
    const tok = loadedToken;
    if (HOST && AUTO && BLOCKED.has(code)) {
      // El equipo de los parlantes salta SOLO si la canción está bloqueada de verdad
      setNotice('Esta canción no está disponible. Pasando a la siguiente…', 'error');
      endedSent = tok;
      setTimeout(() => sendCmd({ c: 'skip', tok: tok }), 1200);
    } else if (BLOCKED.has(code)) {
      setNotice('Esta canción no está disponible en este teléfono; vuelve con la siguiente.', 'error');
    } else {
      setNotice('No se pudo reproducir (código ' + code + '). Toca el vinilo para reintentar.', 'error');
    }
  }

  // ---------- Política de autoplay del navegador ----------
  function armWatchdog() {
    if (watchdog) return;
    watchdog = setTimeout(() => {
      watchdog = null;
      if (!listening || !loadedToken || !S || S.paused || gaveUp || recovering || waitingMore) return;
      const st = player.getPlayerState();
      if (st !== 1 && st !== 3) { player.mute(); player.playVideo(); showUnlock(); }
      else if (player.isMuted()) showUnlock();
    }, 2500);
  }
  function showUnlock() { needTap = true; $('unlock').classList.add('show'); }
  function hideUnlock() { needTap = false; $('unlock').classList.remove('show'); }

  // Debe llamarse dentro de un toque/clic del usuario
  function unlockAndPlay() {
    if (!player || !ready) return;
    hideUnlock();
    player.unMute();
    player.setVolume(+$('volume').value);
    if (!S || !S.token) return;
    const t = targetPos(S);
    if (S.token !== loadedToken) {
      startTrack(S, t);
      return;
    } else {
      if (waitingMore || recovering) return;
      if (gaveUp) { retryTrack(); return; }
      player.seekTo(t, true);
      if (!S.paused) player.playVideo();
    }
    lastSeekAt = now();
    armWatchdog();
  }

  // Reintento manual (toque en el vinilo) después de un fallo
  function retryTrack() {
    if (!S || !S.token || !player || !ready) return;
    loadedToken = '';
    startTrack(S, targetPos(S));
  }

  function setListening(on) {
    listening = on;
    try { localStorage.setItem('mn_listen', on ? '1' : '0'); } catch (e) {}
    root.classList.toggle('listening', on);
    $('listen-text').textContent = on ? 'Escuchando' : 'Escuchar aquí';
    if (on) { unlockAndPlay(); }
    else {
      hideUnlock();
      if (player && ready) player.stopVideo();
      loadedToken = '';
      gaveUp = false;
      waitingMore = false;
      recovering = false;
      clearTimeout(moreTimer);
      setNotice('');
    }
    requestAnimationFrame(fit);
  }
  $('listen-text').textContent = listening ? 'Escuchando' : 'Escuchar aquí';
  $('listen').addEventListener('click', () => setListening(!listening));
  $('unlock').addEventListener('click', (e) => { e.stopPropagation(); unlockAndPlay(); });

  function onAnyGesture(e) {
    if (listening && needTap && e.target !== $('listen') && !$('listen').contains(e.target)) unlockAndPlay();
  }
  ['pointerdown', 'keydown'].forEach((ev) => {
    document.addEventListener(ev, onAnyGesture, true);
    try { P.addEventListener(ev, onAnyGesture, true); } catch (e) {}
  });

  // ---------- Controles del admin ----------
  function togglePlay() {
    if (!HOST || !S || !S.token) return;
    if (S.paused) {
      sendCmd({ c: 'play' });
      if (listening && player && ready) { player.unMute(); player.seekTo(targetPos(S), true); player.playVideo(); lastSeekAt = now(); }
    } else {
      sendCmd({ c: 'pause' });
      if (listening && player && ready) player.pauseVideo();
    }
  }
  $('play').addEventListener('click', togglePlay);
  $('vinyl').addEventListener('click', () => {
    if (listening && gaveUp) { player.unMute(); retryTrack(); return; }
    if (HOST) togglePlay(); else if (!listening) setListening(true);
  });
  $('prev').addEventListener('click', () => sendCmd({ c: 'prev' }));
  $('next').addEventListener('click', () => sendCmd({ c: 'next' }));

  $('progress').addEventListener('input', (e) => {
    if (!HOST || !S) return;
    seeking = true;
    paint(e.target, e.target.value / 10);
    const dur = S.dur || (player && player.getDuration ? player.getDuration() : 0);
    $('cur').textContent = fmt(e.target.value / 1000 * dur);
  });
  $('progress').addEventListener('change', (e) => {
    if (!HOST || !S) return;
    const dur = S.dur || (player && player.getDuration ? player.getDuration() : 0);
    if (dur > 0) {
      const t = e.target.value / 1000 * dur;
      sendCmd({ c: 'seek', t: t });
      if (listening && player && ready) { player.seekTo(t, true); lastSeekAt = now(); }
    }
    seeking = false;
  });

  $('volume').addEventListener('input', (e) => {
    if (player && player.setVolume) { player.setVolume(+e.target.value); if (+e.target.value > 0) player.unMute(); }
    paint(e.target, e.target.value);
  });
  paint($('volume'), 100);

  setInterval(poll, 250);
  setInterval(updateProgress, 500);
  setInterval(follow, 1000);
  poll();
</script>
</body>
</html>
"""


# =========================================================
# VERIFICADOR DE RESULTADOS (prueba cada canción en ESTE dispositivo)
# =========================================================
# Carga cada video en reproductores ocultos y silenciados. Si YouTube lo
# bloquea aquí (error 101/150/100) se prueba la siguiente versión del mismo
# tema; si ninguna funciona, la canción se oculta de los resultados.
PROBE_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<style>
  html, body { margin: 0; background: transparent; overflow: hidden; }
  body { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
  #msg { text-align: center; font-size: 12px; color: #8a8a95; padding: 8px 4px 0; white-space: nowrap;
         overflow: hidden; text-overflow: ellipsis; }
  #msg.warn { color: #ffb020; }
  #pool { position: fixed; left: 0; top: 0; width: 200px; height: 200px; opacity: 0.01; pointer-events: none; z-index: -1; }
  #pool iframe { position: absolute; left: 0; top: 0; width: 200px; height: 200px; border: 0; }
</style>
</head>
<body>
<div id="msg">Comprobando qué canciones se pueden escuchar…</div>
<div id="pool"></div>
<script>
  const ROWS = __ROWS__;
  const P = window.parent.document;
  const MOBILE = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '');
  const WORKERS = 2, TIMEOUT_MS = 7000, TTL_MS = 24 * 3600 * 1000;
  const msg = document.getElementById('msg');

  // ---------- Caché local por dispositivo: vid → [1 ok | 0 bloqueado, fecha] ----------
  let cache = {};
  try { cache = JSON.parse(localStorage.getItem('mn_probe') || '{}'); } catch (e) {}
  const t0 = Date.now();
  for (const v in cache) if (!cache[v] || t0 - cache[v][1] > TTL_MS) delete cache[v];
  function save() { try { localStorage.setItem('mn_probe', JSON.stringify(cache)); } catch (e) {} }

  // ---------- Estado de cada fila: 'pending' | 'ok' | 'bad' ----------
  const rowState = {};
  ROWS.forEach((r) => { rowState[r.k] = 'pending'; });

  function rowEl(k) {
    try { return P.querySelector('.st-key-' + CSS.escape(k)); } catch (e) { return null; }
  }
  function paintRows() {
    ROWS.forEach((r) => {
      const el = rowEl(r.k);
      if (!el) return;
      const st = rowState[r.k];
      el.style.display = st === 'bad' ? 'none' : '';
      el.style.opacity = st === 'pending' ? '0.4' : '';
      el.style.pointerEvents = st === 'pending' ? 'none' : '';
      el.title = st === 'pending' ? 'Comprobando si se puede reproducir…' : '';
    });
  }
  setInterval(paintRows, 400);  // Streamlit puede redibujar las filas: se reaplica

  // ---------- Reportes al servidor (canal oculto) ----------
  const okVids = [], badVids = {};
  function sendCmd(cmd) {
    const input = P.querySelector('.st-key-mn_cmd input');
    if (!input) return;
    cmd.n = Math.random().toString(36).slice(2);
    const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
    setter.call(input, JSON.stringify(cmd));
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
  }

  // ---------- Cola de trabajo: una fila a la vez por reproductor ----------
  const queue = ROWS.map((r) => ({ k: r.k, vids: r.v.slice(), i: 0 }));
  let done = 0;

  function finishRow(job, state) {
    rowState[job.k] = state;
    done++;
    paintRows();
    const visibles = ROWS.filter((r) => rowState[r.k] !== 'bad').length;
    if (done >= ROWS.length) {
      if (!visibles) {
        msg.className = 'warn';
        msg.textContent = '⚠️ YouTube no deja reproducir estas canciones aquí. Prueba otra búsqueda.';
      } else {
        const ocultas = ROWS.length - visibles;
        msg.textContent = ocultas ? '✓ Solo se muestran canciones disponibles (' + ocultas + ' ocultas)' : '';
      }
      if (okVids.length || Object.keys(badVids).length) {
        sendCmd({ c: 'probe', ok: okVids, bad: badVids, m: MOBILE });
      }
      shutdown();
    } else {
      msg.textContent = 'Comprobando qué canciones se pueden escuchar… ' + done + '/' + ROWS.length;
    }
  }

  // Resuelve con la caché local, sin cargar nada, si se puede
  function resolveFromCache(job) {
    while (job.i < job.vids.length) {
      const c = cache[job.vids[job.i]];
      if (!c) return false;            // hay que probarlo de verdad
      if (c[0] === 1) { finishRow(job, 'ok'); return true; }
      job.i++;                          // bloqueado: siguiente versión
    }
    finishRow(job, 'bad');
    return true;
  }

  // ---------- Reproductores de prueba ----------
  const ORIGIN = (() => {
    try { const o = window.parent.location.origin; if (o && o !== 'null') return o; } catch (e) {}
    return '';
  })();

  const workers = [];
  function makeWorker(n) {
    const f = document.createElement('iframe');
    f.id = 'probe' + n;
    f.setAttribute('allow', 'encrypted-media');
    f.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    f.src = 'https://www.youtube.com/embed/?enablejsapi=1&mute=1&controls=0&disablekb=1&fs=0&rel=0' +
            '&playsinline=1&iv_load_policy=3' + (ORIGIN ? '&origin=' + encodeURIComponent(ORIGIN) : '');
    document.getElementById('pool').appendChild(f);
    const w = { player: null, job: null, vid: '', timer: null, okTimer: null, busy: false };
    if (closed) return;
    w.player = new YT.Player(f.id, {
      events: {
        onReady: () => { try { w.player.mute(); } catch (e) {} next(w); },
        // 5 = "video preparado": YouTube aceptó cargarlo en este dispositivo.
        // Se espera un instante por si llega un error de bloqueo justo después.
        onStateChange: (e) => {
          if (!w.busy) return;
          if (e.data === 5) { clearTimeout(w.okTimer); w.okTimer = setTimeout(() => result(w, true), 900); }
          else if (e.data === 1 || e.data === 3) result(w, true);
        },
        onError: (e) => {
          if (!w.busy) return;
          const code = e && e.data;
          // 100/101/150: el video no existe o el dueño bloquea la reproducción aquí
          if (code === 100 || code === 101 || code === 150) result(w, false, code);
          else result(w, null);  // otros errores no dicen nada del video
        },
      },
    });
    workers.push(w);
  }

  // Al terminar se destruyen los reproductores de prueba: en celulares, dejar
  // reproductores extra abiertos le quita recursos al que suena la música.
  let closed = false;
  function shutdown() {
    if (closed) return;
    closed = true;
    try { window.parent.__mnProbing = false; } catch (e) {}
    workers.forEach((w) => { clearTimeout(w.timer); clearTimeout(w.okTimer); try { w.player.destroy(); } catch (e) {} });
    document.getElementById('pool').innerHTML = '';
  }

  function result(w, ok, code) {
    if (!w.busy || closed) return;
    w.busy = false;
    clearTimeout(w.timer);
    clearTimeout(w.okTimer);
    try { w.player.stopVideo(); } catch (e) {}
    const job = w.job, vid = w.vid;
    if (ok === true) {
      cache[vid] = [1, Date.now()]; save();
      okVids.push(vid);
      finishRow(job, 'ok');
    } else if (ok === false) {
      cache[vid] = [0, Date.now()]; save();
      badVids[vid] = code;
      job.i++;
      if (!resolveFromCache(job)) { probe(w, job); return; }  // siguiente versión
    } else {
      finishRow(job, 'ok');  // no concluyente: no se oculta
    }
    next(w);
  }

  function probe(w, job) {
    w.job = job;
    w.vid = job.vids[job.i];
    w.busy = true;
    try { w.player.cueVideoById({ videoId: w.vid }); }
    catch (e) { result(w, null); return; }
    clearTimeout(w.timer);
    w.timer = setTimeout(() => result(w, null), TIMEOUT_MS);
  }

  function next(w) {
    while (queue.length) {
      const job = queue.shift();
      if (resolveFromCache(job)) continue;
      probe(w, job);
      return;
    }
  }

  // Primero lo que ya se sabe en este dispositivo
  for (let i = queue.length - 1; i >= 0; i--) {
    if (resolveFromCache(queue[i])) queue.splice(i, 1);
  }
  paintRows();

  if (!queue.length) shutdown();
  if (queue.length) {
    try { window.parent.__mnProbing = true; } catch (e) {}
    // Nunca queda "verificando" para siempre
    setTimeout(() => { queue.splice(0).forEach((job) => finishRow(job, 'ok'));
                       ROWS.forEach((r) => { if (rowState[r.k] === 'pending') rowState[r.k] = 'ok'; });
                       paintRows(); shutdown(); }, 45000);
    window.onYouTubeIframeAPIReady = () => {
      for (let n = 0; n < Math.min(WORKERS, queue.length); n++) makeWorker(n);
    };
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
    // Si la API de YouTube ni siquiera carga, no se esconde nada
    setTimeout(() => {
      if (!workers.length) {
        queue.splice(0).forEach((job) => finishRow(job, 'ok'));
      }
    }, 15000);
  }
</script>
</body>
</html>
"""

# =========================================================
# FRAGMENTOS EN VIVO
# =========================================================
@st.fragment(run_every=REFRESCO_ESTADO)
def canal_estado():
    """Canal oculto: publica el estado y recibe órdenes del reproductor."""
    room.tick()
    with st.container(key="mn_state"):
        st.text(estado_codificado())
    st.text_input("cmd", key="mn_cmd", label_visibility="collapsed", on_change=on_cmd, args=(ES_HOST,))


def fila(key: str, cancion: dict, numero: int | None = None, acciones=()):
    with st.container(key=key):
        cols = st.columns([1, 6] + [1] * max(1, len(acciones)), vertical_alignment="center")
        with cols[0]:
            if cancion.get("thumbnail"):
                st.image(cancion["thumbnail"], width=44)
        with cols[1]:
            num = f"<span class='li-n'>{numero}</span>" if numero else ""
            extra = []
            if cancion.get("duration"):
                extra.append(html.escape(cancion["duration"]))
            if cancion.get("added_by") == GUEST_ID and not ES_HOST:
                extra.append("<span class='li-me'>tu pedido</span>")
            detalle = " · ".join([html.escape(cancion["artist"])] + extra)
            st.markdown(
                f"<div class='li-t'>{num}{html.escape(cancion['title'])}</div><div class='li-a'>{detalle}</div>",
                unsafe_allow_html=True,
            )
        for i, (col, accion) in enumerate(zip(cols[2:], acciones)):
            with col:
                etiqueta, ayuda, callback, args, deshabilitado = accion
                st.button(etiqueta, key=f"{key}-a{i}", help=ayuda, on_click=callback,
                          args=args, disabled=deshabilitado)


@st.fragment(run_every=REFRESCO_COLA)
def panel_cola():
    playlist, idx, terminado = room.snapshot()
    sonando = not terminado and 0 <= idx < len(playlist)
    proximas = playlist[idx + 1:] if sonando else []
    historial = playlist[:idx] if sonando else playlist

    st.markdown(
        f"<div class='mn-section'><span>A continuación</span><em>{len(proximas)} en espera</em></div>",
        unsafe_allow_html=True,
    )
    if not proximas:
        st.markdown("<div class='mn-empty'>No hay canciones en espera. ¡Pide la próxima! 🎶</div>",
                    unsafe_allow_html=True)

    def acciones_de(c):
        acc = []
        if ES_HOST:
            acc.append((":material/play_arrow:", "Reproducir ahora", room.reproducir, (c["uid"],), False))
        if ES_HOST or c.get("added_by") == GUEST_ID:
            acc.append((":material/close:", "Quitar", room.eliminar, (c["uid"],), False))
        return acc

    for n, c in enumerate(proximas, start=1):
        fila(f"li-q-{c['uid']}", c, numero=n, acciones=acciones_de(c))

    if historial:
        with st.expander(f"Ya sonaron · {len(historial)}"):
            for c in reversed(historial):
                fila(f"li-h-{c['uid']}", c, acciones=acciones_de(c) if ES_HOST else ())

    if ES_HOST and playlist:
        if not st.session_state.get("confirmar_limpiar"):
            if st.button("Vaciar lista", key="btn_vaciar"):
                st.session_state.confirmar_limpiar = True
                st.rerun(scope="fragment")
        else:
            with st.container(key="tools_row"):
                c1, c2 = st.columns(2)
                c1.button("Sí, vaciar todo", on_click=on_limpiar_confirmado, width="stretch")
                if c2.button("Cancelar", width="stretch"):
                    st.session_state.confirmar_limpiar = False
                    st.rerun(scope="fragment")


# =========================================================
# PÁGINA
# =========================================================
st.session_state.setdefault("current_query", "")

st.markdown("<h1 class='mn-title'>MusicNow</h1>", unsafe_allow_html=True)
st.markdown("<p class='mn-sub'>Busca una canción y añádela a la lista</p>", unsafe_allow_html=True)

# HTML constante por dispositivo → el iframe nunca se recarga y la música no se corta
incrustar_html(
    PLAYER_TEMPLATE
    .replace("__HOST__", "true" if ES_HOST else "false")
    .replace("__AUTO__", "true" if AUTO_AUDIO else "false"),
    540 if ES_HOST else 480,
)
canal_estado()

# ---------- Buscador ----------
with st.container(key="search_box"):
    # clear_on_submit=False + key → el texto buscado se queda escrito en la barra
    with st.form(key="search_form", border=False, clear_on_submit=False):
        c_in, c_btn = st.columns([4, 1], vertical_alignment="center")
        with c_in:
            consulta = st.text_input("Búsqueda", placeholder="Canción, artista o género…",
                                     label_visibility="collapsed", max_chars=100,
                                     key="search_input")
        with c_btn:
            buscar = st.form_submit_button("Buscar", width="stretch")
if buscar and consulta.strip():
    st.session_state.current_query = consulta.strip()

flash = st.session_state.pop("flash", None)
aviso_mostrado = False
if flash:
    tipo, mensaje = flash
    if tipo == "ok":
        st.toast(mensaje, icon="🎵")
    else:
        st.markdown(f"<div class='mn-hint' style='color:#ffb020'>{html.escape(mensaje)}</div>",
                    unsafe_allow_html=True)
        aviso_mostrado = True

if not ES_HOST and not aviso_mostrado:
    restante = room.cooldown_restante(GUEST_ID)
    if restante > 0:
        st.markdown(f"<div class='mn-hint'>⏳ Podrás pedir otra canción en {formatear_tiempo(restante)}</div>",
                    unsafe_allow_html=True)

# ---------- Resultados ----------
if st.session_state.current_query:
    q = st.session_state.current_query
    with st.spinner("Buscando…"):
        try:
            resultados, error = buscar_canciones(q), None
        except Exception as e:  # noqa: BLE001
            resultados, error = [], str(e)

    cantidad = f" · {len(resultados)}" if resultados else ""
    st.markdown(
        f"<div class='mn-section'><span>Resultados{cantidad}</span><em>«{html.escape(q)}»</em></div>",
        unsafe_allow_html=True,
    )

    if error:
        st.markdown(f"<div class='mn-empty'>Error al buscar: {html.escape(error)}</div>", unsafe_allow_html=True)
    elif resultados is None:
        st.markdown("<div class='mn-empty'>No se pudo conectar a YouTube Music. Intenta de nuevo.</div>",
                    unsafe_allow_html=True)
    elif not resultados:
        st.markdown("<div class='mn-empty'>Sin resultados para tu búsqueda.</div>", unsafe_allow_html=True)
    else:
        en_cola = room.ids_pendientes()
        # Este mismo dispositivo prueba en silencio cada resultado y oculta
        # los que YouTube no deja reproducir aquí.
        filas_probar = [{"k": f"li-r-{r['video_id']}", "v": [r["video_id"], *r.get("cands", [])][:6]}
                        for r in resultados]
        incrustar_html(PROBE_TEMPLATE.replace("__ROWS__", json.dumps(filas_probar)), 34)
        # Mini scroll: muestra hasta 10 resultados dentro de una caja desplazable
        with st.container(height=ALTO_RESULTADOS, border=False, key="results_scroll"):
            for r in resultados:
                ya = r["video_id"] in en_cola
                fila(
                    f"li-r-{r['video_id']}", r,
                    acciones=[(":material/check:" if ya else ":material/add:",
                               "Ya está en la lista" if ya else "Agregar",
                               on_agregar, (r, GUEST_ID, ES_HOST), ya)],
                )
    st.button("Cerrar resultados", key="btn_cerrar", on_click=on_cerrar_resultados)

# ---------- Cola ----------
panel_cola()


# =========================================================
# INVITAR (QR + WhatsApp)
# =========================================================
@st.cache_data
def generar_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


SHARE_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; background: transparent; }
  body { font-family: 'Inter', system-ui, sans-serif; color: #f5f5f7; padding: 6px 4px; }
  .card {
    display: flex; align-items: center; gap: 22px; padding: 18px;
    background: rgba(22,22,26,0.75); border: 1px solid rgba(255,34,34,0.22); border-radius: 22px;
    box-shadow: 0 0 30px rgba(255,34,34,0.10);
  }
  .qr { background: #fff; padding: 9px; border-radius: 14px; flex-shrink: 0; box-shadow: 0 0 20px rgba(255,34,34,0.25); }
  .qr img { display: block; width: 128px; height: 128px; image-rendering: pixelated; }
  .text { min-width: 0; }
  h3 { margin: 0; font-size: 1.05rem; font-weight: 800; letter-spacing: -0.01em; }
  p { margin: 4px 0 0; font-size: 0.8rem; color: #8a8a95; }
  .url { margin-top: 8px; font-size: 0.78rem; color: #b5b5bf; word-break: break-all; }
  .row { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
  .btn { border: none; border-radius: 999px; padding: 9px 16px; font: 600 0.8rem 'Inter', sans-serif; cursor: pointer;
         text-decoration: none; color: #fff; display: inline-flex; align-items: center; gap: 6px; transition: transform 0.15s; }
  .btn:hover { transform: translateY(-1px); }
  .wa { background: #25D366; box-shadow: 0 4px 14px rgba(37,211,102,0.3); }
  .copy { background: #26262c; }
  @media (max-width: 460px) {
    .card { flex-direction: column; text-align: center; }
    .row { justify-content: center; }
  }
</style>
</head>
<body>
  <div class="card" id="root">
    <div class="qr"><img src="data:image/png;base64,__QR__" alt="Código QR para unirse"></div>
    <div class="text">
      <h3>Invita a la fiesta 📱</h3>
      <p>Escanea el código o comparte el enlace para que todos pidan su música.</p>
      <div class="url">__URL_TEXT__</div>
      <div class="row">
        <a class="btn wa" href="__WA__" target="_blank" rel="noopener">WhatsApp</a>
        <button class="btn copy" id="copy">Copiar enlace</button>
      </div>
    </div>
  </div>
<script>
  const URL_APP = __URL_JSON__;
  function fit() {
    try {
      const f = window.frameElement;
      if (!f) return;
      const h = Math.ceil(document.getElementById('root').getBoundingClientRect().bottom + 14);
      if (Math.abs(f.offsetHeight - h) > 2) { f.style.height = h + 'px'; f.setAttribute('height', h); }
      const box = f.closest('[data-testid="stElementContainer"]');
      if (box && Math.abs(box.offsetHeight - h) > 2) box.style.height = h + 'px';
    } catch (e) {}
  }
  window.addEventListener('resize', fit);
  setTimeout(fit, 50); setTimeout(fit, 600);
  const btn = document.getElementById('copy');
  function done(ok) { btn.textContent = ok ? '¡Copiado!' : 'No se pudo copiar'; setTimeout(() => btn.textContent = 'Copiar enlace', 2000); }
  function fallback() {
    const t = document.createElement('textarea'); t.value = URL_APP; document.body.appendChild(t); t.select();
    let ok = false; try { ok = document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(t); done(ok);
  }
  btn.addEventListener('click', () => {
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(URL_APP).then(() => done(true)).catch(fallback);
    else fallback();
  });
</script>
</body>
</html>
"""

st.markdown("<div class='mn-section'><span>Invitar</span></div>", unsafe_allow_html=True)
incrustar_html(
    SHARE_TEMPLATE
    .replace("__QR__", generar_qr_base64(APP_URL))
    .replace("__URL_TEXT__", html.escape(APP_URL))
    .replace("__WA__", html.escape("https://wa.me/?text=" + quote(f"🎉 ¡Pide tu canción para la fiesta en MusicNow! {APP_URL}")))
    .replace("__URL_JSON__", json.dumps(APP_URL)),
    360,
)


# =========================================================
# ADMIN (discreto, al pie)
# =========================================================
with st.container(key="host_area"):
    with st.popover("🎛️ Admin · activo" if ES_HOST else "🎛️ Soy el admin"):
        if ES_HOST:
            auto = st.toggle("🔊 Reproducir automáticamente en este equipo", value=AUTO_AUDIO,
                             help="Actívalo en el PC o Smart TV conectado a los parlantes. "
                                  "Desactívalo si usas tu teléfono solo como control remoto.")
            if auto != AUTO_AUDIO:
                st.query_params["audio"] = "1" if auto else "0"
                st.rerun()
            st.caption("Si el navegador bloquea el audio, toca el vinilo o cualquier parte de la página una vez.")
            if PIN_POR_DEFECTO:
                st.warning("Estás usando el PIN por defecto. Define `HOST_PIN` en los Secrets de la app.")
            if st.button("Salir del modo admin", width="stretch"):
                for clave in ("host", "audio"):
                    if clave in st.query_params:
                        del st.query_params[clave]
                st.rerun()
        else:
            st.caption("Solo para quien controla la fiesta.")
            with st.form("host_form", border=False):
                pin = st.text_input("PIN", type="password")
                if st.form_submit_button("Entrar", width="stretch"):
                    if pin_valido(pin):
                        st.query_params["host"] = pin
                        st.query_params["audio"] = "1"
                        st.rerun()
                    else:
                        st.error("PIN incorrecto")
