"""Mi Rango de Vocabulario: dos botones, "Rango de vocabulario" y "Rango de
dominio", cada uno con su panel."""
import re

from app import db
from app.models.vocabulario import Vocabulario

RUTA = '/menu/ingles/vocabulario/rango'


def _html(logged_client):
    resp = logged_client.get(RUTA)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def _apertura(html, id_panel):
    encontrado = re.search(rf'<div[^>]*id="{id_panel}"[^>]*>', html)
    assert encontrado, f'no está el panel {id_panel}'
    return encontrado.group(0)


def _calificar_10(logged_client, user):
    palabras = [Vocabulario(idUser=user.idUser, nombre=f'Word{i}', significado=str(i)) for i in range(10)]
    db.session.add_all(palabras)
    db.session.commit()
    for p in palabras:
        logged_client.post('/menu/ingles/vocabulario/calificar',
                           json={'idVocab': p.idVocab, 'nombre': p.nombre, 'calificacion': 'facil'})


def test_muestra_los_dos_botones(logged_client):
    html = _html(logged_client)
    assert 'class="vocab-rank-tabs"' in html
    assert 'data-panel="panel-rango-vocabulario"' in html and 'Rango de vocabulario' in html
    assert 'data-panel="panel-rango-dominio"' in html and 'Rango de dominio' in html


def test_por_defecto_se_ve_el_rango_de_vocabulario(logged_client):
    html = _html(logged_client)
    assert 'hidden' not in _apertura(html, 'panel-rango-vocabulario')
    assert 'hidden' in _apertura(html, 'panel-rango-dominio')


def test_cada_panel_tiene_su_rango(logged_client, user):
    _calificar_10(logged_client, user)
    html = _html(logged_client)
    inicio_vocab = html.index('id="panel-rango-vocabulario"')
    inicio_dominio = html.index('id="panel-rango-dominio"')
    vocab = html[inicio_vocab:inicio_dominio]
    dominio = html[inicio_dominio:]
    assert 'Tu rango de vocabulario' in vocab and 'Has agregado' in vocab
    assert 'Tu rango de dominio' not in vocab
    assert 'Tu rango de dominio' in dominio and 'te resultaron fáciles' in dominio
    assert 'vocab-stat-easy' in dominio  # las cifras Fácil / Medio / Difícil van con el dominio


def test_sin_calificaciones_el_dominio_lo_explica(logged_client):
    html = _html(logged_client)
    dominio = html[html.index('id="panel-rango-dominio"'):]
    assert 'Aún no has calificado ninguna palabra' in dominio


def test_carga_su_js_sin_script_inline(logged_client):
    html = _html(logged_client)
    assert 'js/vocabulario_rango.js' in html
    assert 'vocab-rank-tab' not in ''.join(re.findall(r'<script>(.*?)</script>', html, re.S))
