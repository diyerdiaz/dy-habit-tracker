"""Autocompletar vocabulario gratis: a partir de una palabra en inglés busca sus
significados en español ("casa / hogar") y una frase de ejemplo en inglés.

- Significados: MyMemory (api.mymemory.translated.net), traductor gratis sin clave.
- Ejemplo: Tatoeba (tatoeba.org), frases reales escritas y traducidas por personas.

Ninguno pide API key, así que no hay ningún secreto que guardar.
"""
import json
import os
import re
import threading
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date

URL_MYMEMORY = 'https://api.mymemory.translated.net/get'
URL_TATOEBA = 'https://tatoeba.org/en/api_v0/search'
AGENTE = 'dy-habit-tracker/1.0'
TIEMPO_ESPERA = 12          # segundos por servicio (Tatoeba a veces tarda)
LIMITE_DIARIO_POR_DEFECTO = 40
MAX_LARGO_PALABRA = 60
MAX_SIGNIFICADOS = 4
MAX_LARGO_SIGNIFICADO = 40

# Solo letras (con tildes), espacios, guion y apóstrofo: "give up", "well-known", "don't".
_PALABRA_VALIDA = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ '\-]*$")


class ErrorDiccionario(Exception):
    """No se pudo autocompletar; el mensaje se le puede mostrar al usuario."""


# ── Límite diario por usuario (cuida la cuota gratis de MyMemory) ──

_usos = {}
_usos_lock = threading.Lock()


def _limite_diario():
    try:
        return max(0, int(os.environ.get('DICCIONARIO_LIMITE_DIARIO') or LIMITE_DIARIO_POR_DEFECTO))
    except ValueError:
        return LIMITE_DIARIO_POR_DEFECTO


def registrar_uso(id_user, hoy=None):
    """Cuenta una consulta del usuario hoy. Devuelve False si ya llegó al límite."""
    hoy = hoy or date.today()
    with _usos_lock:
        for clave in [c for c in _usos if c[1] != hoy]:   # se olvidan los días anteriores
            del _usos[clave]
        clave = (id_user, hoy)
        if _usos.get(clave, 0) >= _limite_diario():
            return False
        _usos[clave] = _usos.get(clave, 0) + 1
        return True


def reiniciar_usos():
    with _usos_lock:
        _usos.clear()


# ── Utilidades ──

def limpiar_palabra(texto):
    """La palabra lista para buscar, o None si no es válida."""
    palabra = ' '.join((texto or '').split())
    if not palabra or len(palabra) > MAX_LARGO_PALABRA or not _PALABRA_VALIDA.match(palabra):
        return None
    return palabra


def _sin_tildes(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if unicodedata.category(c) != 'Mn')


def _pedir_json(url, params):
    peticion = urllib.request.Request(f'{url}?{urllib.parse.urlencode(params)}', headers={'User-Agent': AGENTE})
    with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as resp:
        return json.load(resp)


# ── MyMemory: significados ──

def _consultar_mymemory(palabra):
    return _pedir_json(URL_MYMEMORY, {'q': palabra, 'langpair': 'en|es'})


def significados_de(datos, palabra, frases_es=()):
    """Ordena las traducciones de MyMemory de la más fiable a la menos.
    Suben las que más se repiten y las que aparecen en las frases de ejemplo."""
    puntos = defaultdict(float)
    orden = []

    def sumar(texto, valor):
        for parte in texto.split(','):           # "demanda, pánico bancario" -> dos opciones
            t = ' '.join(parte.split()).strip(' .!¡¿?;:"').lower()
            if not t or len(t) > MAX_LARGO_SIGNIFICADO or t == palabra.lower():
                continue
            if t not in puntos:
                orden.append(t)
            puntos[t] += valor

    for m in datos.get('matches') or []:
        if ' '.join(str(m.get('segment', '')).split()).lower() != palabra.lower():
            continue   # traducción de otra frase, no de esta palabra
        try:
            valor = float(m.get('match') or 0) + int(m.get('usage-count') or 0) * 0.1
        except (TypeError, ValueError):
            valor = 0.5
        sumar(str(m.get('translation') or ''), valor)
    sumar(str((datos.get('responseData') or {}).get('translatedText') or ''), 0.5)

    texto_frases = ' '.join(_sin_tildes(f) for f in frases_es)
    for t in orden:
        if texto_frases and re.search(r'\b' + re.escape(_sin_tildes(t)) + r'\b', texto_frases):
            puntos[t] += 2

    return sorted(orden, key=lambda t: -puntos[t])[:MAX_SIGNIFICADOS]


# ── Tatoeba: frase de ejemplo ──

def _consultar_tatoeba(palabra):
    return _pedir_json(URL_TATOEBA, {
        'from': 'eng', 'to': 'spa', 'query': f'="{palabra}"', 'sort': 'relevance',
        'orphans': 'no', 'unapproved': 'no',
        # solo frases con traducción directa al español y de 4 a 10 palabras
        'trans_filter': 'limit', 'trans_to': 'spa', 'trans_link': 'direct',
        'word_count_min': 4, 'word_count_max': 10,
    })


def ejemplos_de(datos, palabra):
    """[(frase en inglés, traducción), ...] que de verdad usan la palabra."""
    # Si la palabra va en minúscula, no vale como nombre propio ("House is a doctor")
    patron = re.compile(r'\b' + re.escape(palabra) + r'\b', 0 if palabra.islower() else re.I)
    ejemplos = []
    for r in datos.get('results') or []:
        texto = ' '.join(str(r.get('text') or '').split())
        directas = (r.get('translations') or [[]])[0] or []
        traduccion = next((t.get('text') for t in directas if t.get('lang') == 'spa' and t.get('text')), None)
        if texto and traduccion and patron.search(texto):
            ejemplos.append((texto, ' '.join(traduccion.split())))
    return ejemplos


# ── Todo junto ──

def autocompletar(palabra):
    """{'significado': 'casa / hogar', 'ejemplo': 'Her house is big.'}
    El ejemplo va solo en inglés; la traducción de la frase solo se usa para
    ordenar mejor los significados.
    Si solo falla el ejemplo, se devuelve el significado con el ejemplo vacío."""
    with ThreadPoolExecutor(max_workers=2) as hilos:   # las dos consultas a la vez
        f_mymemory = hilos.submit(_consultar_mymemory, palabra)
        f_tatoeba = hilos.submit(_consultar_tatoeba, palabra)

    try:
        ejemplos = ejemplos_de(f_tatoeba.result(), palabra)
    except Exception:
        ejemplos = []   # sin ejemplo no pasa nada: se escribe a mano

    try:
        datos = f_mymemory.result()
    except Exception:
        raise ErrorDiccionario('No hay conexión con el traductor. Intenta otra vez o escríbelo a mano.')
    if datos.get('quotaFinished'):
        raise ErrorDiccionario('Se acabó la cuota gratis del traductor por hoy. Escríbelo a mano.')

    significados = significados_de(datos, palabra, [es for _, es in ejemplos])
    if not significados:
        raise ErrorDiccionario(f'No se encontró el significado de "{palabra}".')

    ejemplo = ejemplos[0][0] if ejemplos else ''
    return {'significado': ' / '.join(significados)[:255], 'ejemplo': ejemplo[:500]}
