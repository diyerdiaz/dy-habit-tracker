"""Menú lateral: en el celular "Cerrar sesión" debe verse completo."""
import glob
import os
import re


def _css(app):
    with open(os.path.join(app.static_folder, 'css', 'm.css'), encoding='utf-8') as f:
        return f.read()


def test_menu_mide_lo_visible_en_el_celular(app):
    sidebar = _css(app).split('\n.sidebar {', 1)[1].split('}', 1)[0]
    # 100vh queda de respaldo para navegadores viejos; 100dvh descuenta las barras del navegador
    assert sidebar.index('height: 100vh;') < sidebar.index('height: 100dvh;')
    assert 'env(safe-area-inset-bottom' in sidebar and 'overflow-y: auto;' in sidebar


def test_cerrar_sesion_tiene_su_estilo_propio(app):
    css = _css(app)
    assert '.sidebar-link.sidebar-link-salir {' in css and '.sidebar-link.sidebar-link-salir:hover {' in css


def test_todas_las_plantillas_usan_la_clase_de_cerrar_sesion(app):
    for ruta in glob.glob(os.path.join(app.template_folder, '**', '*.html'), recursive=True):
        with open(ruta, encoding='utf-8') as f:
            html = f.read()
        if 'id="sidebar"' not in html:
            continue
        assert 'sidebar-link-salir' in html, ruta
        assert not re.search(r'class="sidebar-link" style="color: #ff6666', html), ruta


def test_cerrar_sesion_se_ve_en_el_menu(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert 'class="sidebar-link sidebar-link-salir"' in html and 'Cerrar Sesión' in html


# ── Avisos (flash): no deben quedar debajo del menú ni de la campana ──

def test_aviso_de_entrar_en_espanol(client, user):
    from app.test.conftest import TEST_PASSWORD
    resp = client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD}, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert '¡Qué bueno verte de nuevo!' in html and 'Login successful' not in html


def test_avisos_van_en_su_contenedor_y_se_cierran_solos(logged_client):
    with logged_client.session_transaction() as s:
        s['_flashes'] = [('success', 'Aviso de prueba')]
    html = logged_client.get('/dashboard').get_data(as_text=True)
    contenedor = html.split('<div class="avisos" id="avisos">', 1)[1].split('<div class="row', 1)[0]
    assert 'Aviso de prueba' in contenedor
    assert 'js/avisos.js' in html


def test_sin_avisos_no_hay_contenedor(logged_client):
    logged_client.get('/dashboard')   # la primera vez muestra el aviso de bienvenida
    assert 'id="avisos"' not in logged_client.get('/dashboard').get_data(as_text=True)


def test_en_el_celular_el_aviso_va_debajo_de_los_botones_sin_tapar_el_texto(app):
    css = _css(app)
    bloque = css.split('@media (max-width: 768px) {\n    .avisos {', 1)[1].split('}', 1)[0]
    # Ocupa su propio espacio (no flota encima de la página) y empieza debajo del menú (20 a 65 px)
    assert 'position: fixed' not in bloque
    assert 'margin: 0 12px 12px;' in bloque
    # El espacio para no quedar bajo los botones solo va en páginas que tienen el menú
    assert 'body:has(#sidebarToggle) .avisos { padding-top: 52px; }' in css


def test_al_cerrarse_el_aviso_se_encoge(app):
    saliendo = _css(app).split('.flash-message.alert.saliendo {', 1)[1].split('}', 1)[0]
    assert 'max-height: 0 !important;' in saliendo and 'transition:' in saliendo


def test_avisos_js_quita_el_contenedor_vacio(app):
    with open(os.path.join(app.static_folder, 'js', 'avisos.js'), encoding='utf-8') as f:
        js = f.read()
    assert 'contenedor.remove()' in js and "removeAttribute('data-bs-dismiss')" in js


def test_avisos_js_cierra_antes_los_de_exito(app):
    with open(os.path.join(app.static_folder, 'js', 'avisos.js'), encoding='utf-8') as f:
        js = f.read()
    assert 'MS_NORMAL = 4500' in js and 'MS_IMPORTANTE = 8000' in js and "'alert-danger'" in js


def test_menu_lateral_con_la_marca_del_login(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert 'class="menu-marca"' in html and 'icono-loto' in html
    assert 'Habit Tracker<br>&amp; English' in html


def test_todos_los_menus_laterales_traen_la_marca():
    import pathlib
    for plantilla in pathlib.Path('app/templates').rglob('*.html'):
        texto = plantilla.read_text(encoding='utf-8')
        if '<div class="sidebar" id="sidebar">' in texto:
            assert 'menu/_marca_menu.html' in texto, plantilla


def test_diseno_del_login_dentro_de_la_app(client):
    css = client.get('/static/css/m.css').get_data(as_text=True)
    diseno = css[css.index('DISEÑO DE LA PORTADA DENTRO DE LA APP'):]
    # Loto, píldora activa con el degradado del tema y títulos caligráficos
    assert "url('../img/loto.svg')" in diseno
    assert 'linear-gradient(90deg, var(--tema-grad-1' in diseno
    assert "font-family: 'Great Vibes'" in diseno
    assert 'Great+Vibes' in css


# ── Menú de Hábitos por grupos que se despliegan ──

import pytest  # noqa: E402

GRUPOS = {
    'Mis hábitos': ['Gestión de Hábitos', 'Check de Hábitos', 'Recuperar Día', 'Tareas del Día'],
    'Mi progreso': ['Estadísticas', 'Mi Nivel Personal', 'Medallas'],
    'Inspiración y estudio': ['Motivación', 'Métodos de Estudio', 'Vision Board', 'Temas Aleatorios'],
}


def _menu(html):
    return html.split('id="sidebar"', 1)[1].split('id="sidebarOverlay"', 1)[0]


def _grupo(menu, titulo):
    """HTML del <details> cuyo título es `titulo`."""
    inicio = menu.rindex('<details', 0, menu.index(f'<span>{titulo}</span>'))
    return menu[inicio:menu.index('</details>', inicio)]


def test_cada_boton_esta_en_su_grupo(logged_client):
    menu = _menu(logged_client.get('/dashboard').get_data(as_text=True))
    for titulo, botones in GRUPOS.items():
        grupo = _grupo(menu, titulo)
        assert 'name="menu-grupo"' in grupo
        for boton in botones:
            assert boton in grupo, (titulo, boton)
    # Inicio, perfil y cerrar sesión quedan fuera de los grupos, siempre a la vista
    assert menu.index('</i> Inicio') < menu.index('<details')
    assert menu.rindex('</details>') < menu.index('Mi Perfil') < menu.index('sidebar-link-salir')


def test_en_el_inicio_los_grupos_empiezan_cerrados(logged_client):
    menu = _menu(logged_client.get('/dashboard').get_data(as_text=True))
    assert ' open>' not in menu
    assert 'href="/dashboard" class="sidebar-link active"' in menu


@pytest.mark.parametrize('url, grupo, boton', [
    ('/tareas/', 'Mis hábitos', 'Tareas del Día'),
    ('/register_habit', 'Mis hábitos', 'Gestión de Hábitos'),
    ('/estadisticas/', 'Mi progreso', 'Estadísticas'),
    ('/menu/nivel', 'Mi progreso', 'Mi Nivel Personal'),
    ('/medallas/', 'Mi progreso', 'Medallas'),
    ('/motivacion/', 'Inspiración y estudio', 'Motivación'),
    ('/temas/', 'Inspiración y estudio', 'Temas Aleatorios'),
])
def test_se_abre_el_grupo_de_la_pagina_actual(logged_client, url, grupo, boton):
    menu = _menu(logged_client.get(url, follow_redirects=True).get_data(as_text=True))
    abierto = _grupo(menu, grupo)
    assert abierto.startswith('<details class="menu-grupo" name="menu-grupo" open>'), url
    assert menu.count(' open>') == 1, url
    activo = abierto.split('sidebar-link active', 1)[1].split('</a>', 1)[0]
    assert boton in activo, url


def test_todas_las_paginas_de_habitos_usan_el_menu_compartido(app):
    for ruta in glob.glob(os.path.join(app.template_folder, '**', '*.html'), recursive=True):
        with open(ruta, encoding='utf-8') as f:
            html = f.read()
        if 'id="sidebar"' in html:
            assert os.path.basename(ruta).startswith('_sidebar_'), ruta


def test_css_de_los_grupos(app):
    css = _css(app)
    assert '.menu-grupo-titulo::-webkit-details-marker { display: none; }' in css
    assert '.menu-grupo[open] .menu-grupo-flecha { transform: rotate(180deg); }' in css
