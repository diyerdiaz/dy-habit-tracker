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
