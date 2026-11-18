"""Interruptor Hábitos | Inglés | Español del menú lateral y el menú propio de cada sección."""
import glob
import os

import pytest

PAGINAS_HABITOS = ['/dashboard', '/tareas/', '/medallas/', '/perfil/']
PAGINAS_INGLES = [
    '/menu/ingles',
    '/menu/ingles/vocabulario',
    '/menu/ingles/shadowing',
    '/menu/ingles/palabras-aleatorias',
    '/menu/ingles/pronunciacion',
    '/menu/ingles/juegos/',
]
BOTONES_INGLES = ['Inicio Inglés', 'Vocabulario', 'Shadowing', 'Juegos', 'Palabras aleatorias', 'Pronunciación']


def _html(client, url):
    resp = client.get(url, follow_redirects=True)
    assert resp.status_code == 200, url
    return resp.get_data(as_text=True)


def _menu(html):
    return html.split('id="sidebar"', 1)[1].split('id="sidebarOverlay"', 1)[0]


@pytest.mark.parametrize('url', PAGINAS_HABITOS + PAGINAS_INGLES + ['/menu/espanol'])
def test_el_interruptor_tiene_las_tres_secciones(logged_client, url):
    menu = _menu(_html(logged_client, url))
    for seccion in ('Hábitos', 'Inglés', 'Español'):
        assert f'</i> {seccion}' in menu, (url, seccion)
    assert 'href="/menu/espanol"' in menu


@pytest.mark.parametrize('url', PAGINAS_HABITOS)
def test_en_habitos_el_menu_es_de_habitos(logged_client, url):
    menu = _menu(_html(logged_client, url))
    assert 'sidebar-toggle toggle-habitos' in menu
    assert '/register_habit"' in menu and 'Inicio Inglés' not in menu


@pytest.mark.parametrize('url', PAGINAS_INGLES)
def test_en_ingles_el_menu_solo_tiene_botones_de_ingles(logged_client, url):
    menu = _menu(_html(logged_client, url))
    assert 'sidebar-toggle toggle-ingles' in menu
    for boton in BOTONES_INGLES:
        assert boton in menu, (url, boton)
    for de_habitos in ('Registrar Hábito', 'Check de Hábitos', 'Tareas del Día', 'Medallas', 'Vision Board'):
        assert de_habitos not in menu, (url, de_habitos)
    # Perfil y cerrar sesión siguen en todas las secciones
    assert 'Mi Perfil' in menu and 'sidebar-link-salir' in menu


def test_en_ingles_se_resalta_la_pagina_actual(logged_client):
    menu = _menu(_html(logged_client, '/menu/ingles/vocabulario'))
    assert 'href="/menu/ingles/vocabulario" class="sidebar-link active"' in menu
    assert 'href="/menu/ingles" class="sidebar-link active"' not in menu


def test_ninguna_plantilla_copia_el_interruptor(app):
    """El interruptor vive solo en menu/_switch_seccion.html: así no quedan menús con 2 opciones."""
    for ruta in glob.glob(os.path.join(app.template_folder, '**', '*.html'), recursive=True):
        if ruta.endswith('_switch_seccion.html'):
            continue
        with open(ruta, encoding='utf-8') as f:
            assert 'sidebar-toggle-thumb' not in f.read(), ruta


def test_las_paginas_de_ingles_usan_el_menu_de_ingles(app):
    carpeta = os.path.join(app.template_folder, 'ingles')
    for ruta in glob.glob(os.path.join(carpeta, '*.html')):
        with open(ruta, encoding='utf-8') as f:
            html = f.read()
        if 'id="sidebar"' in html:
            assert ruta.endswith('_sidebar_ingles.html'), ruta


def test_css_del_interruptor_tiene_tres_posiciones(app):
    with open(os.path.join(app.static_folder, 'css', 'm.css'), encoding='utf-8') as f:
        css = f.read()
    assert 'width: calc((100% - 8px) / 3);' in css
    assert '.sidebar-toggle.toggle-ingles .sidebar-toggle-thumb' in css
    assert '.sidebar-toggle.toggle-espanol .sidebar-toggle-thumb' in css


def test_el_interruptor_toma_el_color_de_la_seccion(app):
    """Antes era siempre azul: ahora usa los colores del tema de la página."""
    with open(os.path.join(app.static_folder, 'css', 'm.css'), encoding='utf-8') as f:
        css = f.read()
    bloque = css.split('\n.sidebar-toggle {', 1)[1].split('}', 1)[0]
    assert 'var(--tema-grad-1' in bloque and 'var(--tema-grad-2' in bloque
    assert '#0d6efd' not in bloque
    # Cada sección define esos colores en su propio CSS
    for hoja in ('ingles.css', 'espanol.css'):
        with open(os.path.join(app.static_folder, 'css', hoja), encoding='utf-8') as f:
            assert '--tema-grad-1:' in f.read(), hoja
