"""Sección Español: por ahora una página propia con su menú (contenido 'próximamente')."""


def test_espanol_pide_sesion(client):
    assert client.get('/menu/espanol').status_code == 302


def test_espanol_se_abre_con_su_menu(logged_client):
    html = logged_client.get('/menu/espanol').get_data(as_text=True)
    assert 'Inicio Español' in html and 'Próximamente' in html
    # El menú de Español no muestra los botones de hábitos ni los de inglés
    assert 'Registrar Hábito' not in html and 'Shadowing' not in html
    assert 'css/espanol.css' in html and 'js/sidebar.js' in html


def test_espanol_marca_su_opcion_en_el_interruptor(logged_client):
    html = logged_client.get('/menu/espanol').get_data(as_text=True)
    assert 'sidebar-toggle toggle-espanol' in html
    assert 'href="/menu/espanol" class="sidebar-toggle-option active-side"' in html
    assert 'sidebar-link-salir' in html and 'Mi Perfil' in html
