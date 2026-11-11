"""Vocabulario: tiempo mínimo en cada tarjeta y sesiones guardadas aunque se
salga a mitad (lo estudiado cuenta en el momento, no al terminar la ronda)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import db
from app.models.vocabulario import Vocabulario
from app.models.vocabulario_registro import VocabularioRegistro
from app.services.ingles import TIEMPOS_TARJETA, TIEMPO_TARJETA_POR_DEFECTO

JS = Path(__file__).resolve().parents[1] / 'static' / 'js' / 'vocabulario.js'
RUTA = '/menu/ingles/vocabulario/aprender'


def _node(cuerpo):
    """Corre `cuerpo` con las funciones del JS real ya cargadas y devuelve su JSON."""
    if not shutil.which('node'):
        pytest.skip('node no está instalado')
    codigo = f"""
global.document = {{ getElementById: () => null, querySelectorAll: () => [], addEventListener: () => {{}} }};
const js = require({json.dumps(str(JS))});
{cuerpo}
"""
    salida = subprocess.run(['node', '-e', codigo], capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


def _crear_palabras(user, cantidad):
    palabras = [Vocabulario(idUser=user.idUser, nombre=f'Word{i}', significado=f'Palabra {i}') for i in range(cantidad)]
    db.session.add_all(palabras)
    db.session.commit()
    return palabras


def _calificar(logged_client, palabra, calificacion):
    return logged_client.post('/menu/ingles/vocabulario/calificar',
                              json={'idVocab': palabra.idVocab, 'nombre': palabra.nombre, 'calificacion': calificacion})


# ── Tiempo mínimo por tarjeta ──

def test_se_elige_el_tiempo_minimo_al_empezar(logged_client, user):
    _crear_palabras(user, 3)
    html = logged_client.get(RUTA).get_data(as_text=True)
    assert 'id="vocabTiempo"' in html and 'Tiempo mínimo en cada tarjeta' in html
    opciones = re.findall(r'<option value="(\d+)"\s*(selected)?>([^<]*)</option>',
                          html[html.index('id="vocabTiempo"'):])[:len(TIEMPOS_TARJETA)]
    assert [int(v) for v, _, _ in opciones] == TIEMPOS_TARJETA
    assert [int(v) for v, sel, _ in opciones if sel] == [TIEMPO_TARJETA_POR_DEFECTO]
    assert opciones[0][2] == 'Sin mínimo' and opciones[1][2] == '5 segundos'


def test_la_tarjeta_tiene_cuenta_regresiva(logged_client, user):
    _crear_palabras(user, 1)
    html = logged_client.get(RUTA).get_data(as_text=True)
    assert 'id="vocabEspera"' in html and 'id="vocabEsperaTexto"' in html


def test_segundos_restantes():
    resultado = _node("""
console.log(JSON.stringify([
    js.vocabSegundosRestantes(0, 0, 10),      // recién mostrada
    js.vocabSegundosRestantes(0, 3200, 10),   // van 3,2 s
    js.vocabSegundosRestantes(0, 9001, 10),   // falta menos de 1 s
    js.vocabSegundosRestantes(0, 10000, 10),  // justo se cumple
    js.vocabSegundosRestantes(0, 60000, 10),  // ya pasó de sobra
    js.vocabSegundosRestantes(0, 0, 0),       // sin mínimo
]));
""")
    assert resultado == [10, 7, 1, 0, 0, 0]


def test_no_se_puede_calificar_antes_del_tiempo():
    js = JS.read_text()
    # Los botones se desactivan y el clic se ignora hasta que se cumpla el tiempo
    assert 'if (!vocabPuedePasar) return;' in js
    assert "b.disabled = !activos" in js
    assert 'vocabBotonesCalificar(false);' in js


# ── Salir a mitad: lo estudiado ya cuenta ──

def test_hay_boton_para_terminar_a_mitad(logged_client, user):
    _crear_palabras(user, 2)
    html = logged_client.get(RUTA).get_data(as_text=True)
    assert 'id="vocabTerminarBtn"' in html and 'Terminar aquí' in html


def test_cada_tarjeta_se_guarda_al_calificarla_aunque_se_salga(logged_client, user):
    """Estudiar 5 de 10 y salir: las 5 quedan guardadas, las otras no."""
    palabras = _crear_palabras(user, 10)
    for p in palabras[:5]:
        assert _calificar(logged_client, p, 'medio').status_code == 200
    assert VocabularioRegistro.query.filter_by(idUser=user.idUser).count() == 5

    # Al volver a la página, esas 5 ya cuentan como vistas y la ronda empieza por las otras 5
    html = logged_client.get(RUTA).get_data(as_text=True)
    datos = json.loads(re.search(r'window\.VOCAB_PALABRAS = (.*?);\n', html).group(1))
    vistas = {d['nombre'] for d in datos if d['vecesMostrada'] == 1}
    assert vistas == {p.nombre for p in palabras[:5]}


def test_el_envio_sobrevive_a_salir_de_la_pagina():
    assert 'keepalive: true' in JS.read_text()


def test_sin_recargar_la_siguiente_ronda_ya_cuenta_lo_estudiado():
    """Antes la página se quedaba con los datos viejos hasta recargar."""
    resultado = _node("""
const palabras = [
    { idVocab: 1, nombre: 'A', vecesMostrada: 0, peso: 2, ultimaCalificacion: null },
    { idVocab: 2, nombre: 'B', vecesMostrada: 0, peso: 2, ultimaCalificacion: null },
    { idVocab: 3, nombre: 'C', vecesMostrada: 0, peso: 2, ultimaCalificacion: null },
    { idVocab: 4, nombre: 'D', vecesMostrada: 0, peso: 2, ultimaCalificacion: null },
];
// Primera ronda a medias: A fácil, B difícil, y se sale
js.vocabRegistrarCalificacion(palabras, 1, 'facil');
js.vocabRegistrarCalificacion(palabras, 2, 'dificil');
const b = palabras[1];
const rondas = [];
for (let i = 0; i < 200; i++) rondas.push(js.vocabSeleccionPonderada(palabras, 3).map((p) => p.nombre));
console.log(JSON.stringify({ b, rondas }));
""")
    assert resultado['b']['vecesMostrada'] == 1 and resultado['b']['ultimaCalificacion'] == 'dificil'
    assert resultado['b']['peso'] == 3
    for ronda in resultado['rondas']:
        assert ronda[0] == 'B'                   # la difícil va primero
        assert set(ronda[1:]) == {'C', 'D'}      # luego las que no se estudiaron; A espera su turno


def test_resumen_dice_cuantas_se_estudiaron():
    js = JS.read_text()
    assert 'Sesión guardada' in js and '${estudiadas} de ${total}' in js
    assert 'No calificaste ninguna palabra' in js


def test_sin_script_inline_nuevo(logged_client, user):
    _crear_palabras(user, 1)
    html = logged_client.get(RUTA).get_data(as_text=True)
    inline = ''.join(re.findall(r'<script>(.*?)</script>', html, re.S))
    assert 'vocabTiempo' not in inline and 'vocabTerminar' not in inline


def test_los_desplegables_usan_lista_oscura(logged_client, user):
    """La lista abierta de palabras y de segundos va con fondo oscuro y letras claras."""
    _crear_palabras(user, 2)
    html = logged_client.get(RUTA).get_data(as_text=True)
    assert re.search(r'<select id="vocabCantidad" class="[^"]*glass-input', html)
    assert re.search(r'<select id="vocabTiempo" class="[^"]*glass-input', html)
    css = (JS.parents[1] / 'css' / 'vocabulario.css').read_text()
    assert '.glass-input { color-scheme: dark; }' in css
    assert '.glass-input option { background: #002347; color: #fff; }' in css


def test_el_tiempo_empieza_al_ver_el_significado(logged_client, user):
    """La cuenta regresiva va junto al significado y arranca al pulsar "Ver significado"."""
    _crear_palabras(user, 1)
    html = logged_client.get(RUTA).get_data(as_text=True)
    # Va debajo de los botones Fácil / Medio fácil / Difícil, dentro del reverso
    assert html.index('id="vocabFlashBack"') < html.index('data-rating="dificil"') < html.index('id="vocabEspera"')
    assert html.index('id="vocabEspera"') < html.index('id="vocabSummary"')
    assert 'Empieza a contar cuando veas el significado' in html

    js = JS.read_text()
    revelar = js[js.index("vocabRevelarBtn.addEventListener('click'"):]
    revelar = revelar[:revelar.index('});')]
    assert 'vocabIniciarTemporizador();' in revelar
    # Al mostrar una tarjeta nueva el tiempo no corre todavía y no se puede calificar
    mostrar = js[js.index('function vocabMostrarPalabra()'):js.index('function vocabMostrarResumen()')]
    assert 'vocabIniciarTemporizador' not in mostrar
    assert 'vocabBotonesCalificar(false);' in mostrar
