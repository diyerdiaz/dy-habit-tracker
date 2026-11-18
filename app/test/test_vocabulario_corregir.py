"""Aprender Vocabulario: volver a la tarjeta anterior para corregir la
calificación (se le dio a Fácil / Medio / Difícil por error)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app import db
from app.models.vocabulario import Vocabulario
from app.models.vocabulario_registro import VocabularioRegistro

JS = Path(__file__).resolve().parents[1] / 'static' / 'js' / 'vocabulario.js'
RUTA = '/menu/ingles/vocabulario/aprender'
CALIFICAR = '/menu/ingles/vocabulario/calificar'


def _node(cuerpo):
    if not shutil.which('node'):
        pytest.skip('node no está instalado')
    codigo = f"""
global.document = {{ getElementById: () => null, querySelectorAll: () => [], addEventListener: () => {{}} }};
const js = require({json.dumps(str(JS))});
{cuerpo}
"""
    salida = subprocess.run(['node', '-e', codigo], capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


def _palabra(user, nombre='House'):
    p = Vocabulario(idUser=user.idUser, nombre=nombre, significado='Casa')
    db.session.add(p)
    db.session.commit()
    return p


def _calificar(client, palabra, calificacion):
    return client.post(CALIFICAR, json={'idVocab': palabra.idVocab, 'nombre': palabra.nombre,
                                        'calificacion': calificacion})


# ── Servidor ──

def test_calificar_devuelve_el_id_del_registro(logged_client, user):
    p = _palabra(user)
    datos = _calificar(logged_client, p, 'facil').get_json()
    registro = VocabularioRegistro.query.filter_by(idUser=user.idUser).one()
    assert datos == {'success': True, 'idRegistro': registro.idRegistro}


def test_corregir_cambia_el_mismo_registro_sin_sumar_otro(logged_client, user):
    p = _palabra(user)
    id_registro = _calificar(logged_client, p, 'facil').get_json()['idRegistro']

    resp = logged_client.post(f'{CALIFICAR}/{id_registro}/corregir', json={'calificacion': 'dificil'})
    assert resp.status_code == 200 and resp.get_json() == {'success': True}

    registros = VocabularioRegistro.query.filter_by(idUser=user.idUser).all()
    assert len(registros) == 1 and registros[0].calificacion == 'dificil'


def test_tras_corregir_la_pagina_ve_la_nueva_calificacion(logged_client, user):
    p = _palabra(user)
    id_registro = _calificar(logged_client, p, 'facil').get_json()['idRegistro']
    logged_client.post(f'{CALIFICAR}/{id_registro}/corregir', json={'calificacion': 'dificil'})

    html = logged_client.get(RUTA).get_data(as_text=True)
    datos = json.loads(html.split('window.VOCAB_PALABRAS = ', 1)[1].split(';\n', 1)[0])
    assert datos[0]['ultimaCalificacion'] == 'dificil'
    assert datos[0]['vecesMostrada'] == 1   # corregir no cuenta como otra vez


def test_corregir_con_calificacion_invalida_falla(logged_client, user):
    p = _palabra(user)
    id_registro = _calificar(logged_client, p, 'facil').get_json()['idRegistro']
    resp = logged_client.post(f'{CALIFICAR}/{id_registro}/corregir', json={'calificacion': 'otra'})
    assert resp.status_code == 400
    assert db.session.get(VocabularioRegistro, id_registro).calificacion == 'facil'


def test_no_se_puede_corregir_el_registro_de_otro_usuario(logged_client, user, other_user):
    ajeno = VocabularioRegistro(idUser=other_user.idUser, palabraNombre='Dog', calificacion='facil')
    db.session.add(ajeno)
    db.session.commit()

    resp = logged_client.post(f'{CALIFICAR}/{ajeno.idRegistro}/corregir', json={'calificacion': 'dificil'})
    assert resp.status_code == 404
    assert db.session.get(VocabularioRegistro, ajeno.idRegistro).calificacion == 'facil'


# ── Página ──

def test_la_tarjeta_tiene_boton_anterior(logged_client, user):
    _palabra(user)
    html = logged_client.get(RUTA).get_data(as_text=True)
    assert 'id="vocabAnteriorBtn"' in html and 'Anterior' in html
    assert 'id="vocabCorregirUltimaBtn"' in html and 'Corregir la última' in html
    assert 'id="vocabCorrigiendo"' in html


# ── JS ──

def test_corregir_cambia_la_dificultad_pero_no_las_veces():
    resultado = _node("""
const palabras = [{ idVocab: 1, nombre: 'A', vecesMostrada: 0, peso: 2, ultimaCalificacion: null }];
js.vocabRegistrarCalificacion(palabras, 1, 'facil');
js.vocabCorregirCalificacion(palabras, 1, 'dificil');
console.log(JSON.stringify(palabras[0]));
""")
    assert resultado['vecesMostrada'] == 1
    assert resultado['ultimaCalificacion'] == 'dificil' and resultado['peso'] == 3


def test_resumen_cuenta_las_calificaciones_ya_corregidas():
    resultado = _node("""
const respuestas = [{ rating: 'facil' }, { rating: 'dificil' }, { rating: 'facil' }];
respuestas[0].rating = 'medio';   // se volvió y se corrigió
console.log(JSON.stringify(js.vocabContarCalificaciones(respuestas)));
""")
    assert resultado == {'facil': 1, 'medio': 1, 'dificil': 1}
