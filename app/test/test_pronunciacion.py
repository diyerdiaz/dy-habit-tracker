"""Práctica de pronunciación: pegar un texto, leerlo con el micrófono y ver las palabras en verde o rojo."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parents[1] / 'static' / 'js' / 'pronunciacion.js'


def test_pronunciacion_requiere_login(client):
    assert client.get('/menu/ingles/pronunciacion').status_code == 302


def test_pagina_tiene_la_carpeta_y_el_boton_iniciar(logged_client):
    html = logged_client.get('/menu/ingles/pronunciacion').get_data(as_text=True)
    assert 'class="pron-carpeta' in html and 'Mi texto' in html
    assert 'id="pronTexto"' in html and 'id="pronIniciar"' in html
    assert 'js/pronunciacion.js' in html and 'css/pronunciacion.css' in html


def test_tarjeta_en_el_menu_de_ingles(logged_client):
    html = logged_client.get('/menu/ingles').get_data(as_text=True)
    assert '/menu/ingles/pronunciacion' in html and 'Pronunciación' in html


def test_reconoce_en_ingles(logged_client):
    js = logged_client.get('/static/js/pronunciacion.js').get_data(as_text=True)
    assert "lang = 'en-US'" in js


# ── La comparación de palabras (se corre el mismo JS con node) ──

def _comparar(texto, dicho):
    if not shutil.which('node'):
        pytest.skip('node no está instalado')
    codigo = (
        f"const p = require({json.dumps(str(JS))});"
        f"console.log(JSON.stringify(p.comparar(p.palabrasDichas({json.dumps(texto)}),"
        f" p.palabrasDichas({json.dumps(dicho)}))));"
    )
    salida = subprocess.run(['node', '-e', codigo], capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


def test_palabras_bien_mal_y_pendientes():
    assert _comparar('Hello world, how are you?', 'hello word how') == \
        ['bien', 'mal', 'bien', 'pendiente', 'pendiente']


def test_una_palabra_saltada_no_pinta_todo_de_rojo():
    assert _comparar('one two three four', 'one three four') == ['bien', 'mal', 'bien', 'bien']


def test_una_palabra_de_mas_no_cuenta_como_error():
    assert _comparar('I like dogs', 'I really like dogs') == ['bien', 'bien', 'bien']


def test_ignora_mayusculas_signos_y_numeros_escritos():
    assert _comparar("I DON’T have 5 cats!", "i don't have five cats") == ['bien'] * 5


def test_sin_hablar_todo_queda_pendiente():
    assert _comparar('a b c', '') == ['pendiente'] * 3


def test_avisa_que_brave_no_sirve(logged_client):
    js = logged_client.get('/static/js/pronunciacion.js').get_data(as_text=True)
    assert 'navigator.brave' in js and 'Brave no permite el reconocimiento de voz' in js
