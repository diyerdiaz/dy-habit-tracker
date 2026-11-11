"""Mi Nivel Personal: dos botones ("Mi nivel" y "Niveles") en vez del mapa debajo."""
import re

from flask import url_for


def _html_nivel(logged_client, app):
    with app.test_request_context():
        ruta = url_for('menu.nivel')
    respuesta = logged_client.get(ruta)
    assert respuesta.status_code == 200
    return respuesta.get_data(as_text=True)


def _panel(html, id_panel):
    """Etiqueta de apertura del panel con ese id."""
    encontrado = re.search(rf'<div[^>]*id="{id_panel}"[^>]*>', html)
    assert encontrado, f'no está el panel {id_panel}'
    return encontrado.group(0)


def test_nivel_muestra_los_dos_botones(logged_client, app):
    html = _html_nivel(logged_client, app)
    assert 'class="nivel-tabs"' in html
    assert 'data-panel="panel-mi-nivel"' in html and 'Mi nivel' in html
    assert 'data-panel="panel-niveles"' in html and 'Niveles' in html


def test_por_defecto_se_ve_mi_nivel_y_el_mapa_esta_oculto(logged_client, app):
    html = _html_nivel(logged_client, app)
    assert 'hidden' not in _panel(html, 'panel-mi-nivel')
    assert 'hidden' in _panel(html, 'panel-niveles')


def test_cada_panel_tiene_su_contenido(logged_client, app):
    html = _html_nivel(logged_client, app)
    inicio_mi_nivel = html.index('id="panel-mi-nivel"')
    inicio_niveles = html.index('id="panel-niveles"')
    # El nivel actual y el camino al máximo van en "Mi nivel"; el mapa, en "Niveles"
    assert inicio_mi_nivel < html.index('class="nivel-card"') < inicio_niveles
    assert inicio_mi_nivel < html.index('class="nivel-camino-card"') < inicio_niveles
    assert html.index('class="nivel-mapa-card"') > inicio_niveles
    assert html.count('class="nivel-mapa-item') == 10


def test_nivel_carga_su_js_sin_script_inline(logged_client, app):
    html = _html_nivel(logged_client, app)
    assert 'js/nivel.js' in html
    assert 'nivel-tab' not in ''.join(re.findall(r'<script>(.*?)</script>', html, re.S))
