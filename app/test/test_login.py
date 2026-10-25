import re
from app.models.personajes_login import PERSONAJES, elegir_personaje, tema_del_sitio
from app.test.conftest import TEST_PASSWORD


def test_login_success(client, user):
    response = client.post('/', data={
        'nameUser': user.nameUser,
        'passwordUser': TEST_PASSWORD,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "Hábitos de Hoy".encode() in response.data


def test_login_invalid_credentials(client, user):
    response = client.post('/', data={
        'nameUser': user.nameUser,
        'passwordUser': 'clave_incorrecta',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "Usuario o contraseña incorrectos" in response.get_data(as_text=True)


def test_password_is_stored_hashed(user):
    assert user.passwordUser != TEST_PASSWORD
    assert user.password_is_hashed()


def test_legacy_plaintext_password_is_upgraded_on_login(app, client):
    from app import db
    from app.models.users import User
    legacy = User(nameUser="viejo")
    legacy.passwordUser = "clave_vieja"   # simula un registro antiguo en texto plano
    db.session.add(legacy)
    db.session.commit()

    response = client.post('/', data={'nameUser': 'viejo', 'passwordUser': 'clave_vieja'})
    assert response.status_code == 302
    assert db.session.get(User, legacy.idUser).password_is_hashed()


def test_dashboard_requires_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302


def test_login_already_authenticated(logged_client):
    response = logged_client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert "Hábitos de Hoy".encode() in response.data


def test_login_sin_portafolio_ni_descarga_de_apk(client):
    html = client.get('/').get_data(as_text=True)
    assert 'Iniciar sesión' in html
    assert 'Mi Portafolio' not in html
    assert 'Descargar app para Android' not in html


def test_login_muestra_personaje_anime(client):
    html = client.get('/').get_data(as_text=True)
    assert 'class="login-personaje"' in html
    for p in PERSONAJES:
        assert client.get('/static/img/' + p['archivo']).status_code == 200


def test_personaje_cambia_en_cada_recarga(client):
    anterior = None
    vistos = set()
    for _ in range(30):
        html = client.get('/').get_data(as_text=True)
        actual = re.search(r'img/(personajes/personaje-\d\.svg)', html).group(1)
        assert actual != anterior
        vistos.add(actual)
        anterior = actual
    assert len(vistos) > 1


def test_elegir_personaje_nunca_repite_el_anterior():
    for anterior in range(len(PERSONAJES)):
        for _ in range(20):
            assert elegir_personaje(anterior) != anterior
    assert 0 <= elegir_personaje(None) < len(PERSONAJES)


def test_bienvenida_despues_de_iniciar_sesion(client, user):
    resp = client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD},
                       follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert 'id="bienvenida"' in html and 'data-login="1"' in html
    assert f'Bienvenido, {user.nameUser}' in html
    assert 'js/bienvenida.js' in html and 'css/bienvenida.css' in html


def test_bienvenida_tambien_al_volver_sin_cerrar_sesion(logged_client, user):
    # Con la sesión abierta el saludo sigue en la página; bienvenida.js decide
    # mostrarlo si es una visita nueva (pestaña o app recién abierta)
    logged_client.get('/dashboard')
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert f'Bienvenido, {user.nameUser}' in html
    assert 'data-login="0"' in html


def test_bienvenida_no_se_repite_en_la_misma_visita():
    with open('app/static/js/bienvenida.js') as f:
        js = f.read()
    assert 'sessionStorage' in js and "dataset.login !== '1'" in js


def test_la_cueva_ya_no_existe(client, user):
    # La animación pesada de la cueva se trababa en el celular; quedó solo el saludo
    resp = client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD},
                       follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert 'cueva' not in html
    assert client.get('/static/js/entrada_cueva.js').status_code == 404


def test_bienvenida_es_liviana():
    # Sin desenfoques ni filtros SVG: son los que traban la animación en el celular
    with open('app/static/css/bienvenida.css') as f:
        css = f.read()
    assert 'blur(' not in css and 'filter:' not in css


def test_login_fallido_no_muestra_bienvenida(client, user):
    client.post('/', data={'nameUser': user.nameUser, 'passwordUser': 'mala'})
    assert client.get('/dashboard').status_code == 302
    with client.session_transaction() as s:
        assert 'bienvenida' not in s


def test_cada_personaje_trae_su_paleta_completa():
    vivos = set()
    for p in PERSONAJES:
        vivos.add(p['tema']['vivo'])
    assert len(vivos) == len(PERSONAJES)  # cada uno de un color distinto


def test_el_fondo_del_login_usa_el_color_del_personaje(client):
    for _ in range(5):
        html = client.get('/').get_data(as_text=True)
        archivo = re.search(r'img/(personajes/personaje-\d\.svg)', html).group(1)
        personaje = next(p for p in PERSONAJES if p['archivo'] == archivo)
        assert f"--tema-vivo: {personaje['tema']['vivo']};" in html
        assert 'class="login-fondo"' in html


def _personaje_del_login(client):
    html = client.get('/').get_data(as_text=True)
    archivo = re.search(r'img/(personajes/personaje-\d\.svg)', html).group(1)
    return next(p for p in PERSONAJES if p['archivo'] == archivo)


def test_toda_la_app_toma_el_color_del_personaje_del_login(client, user):
    personaje = _personaje_del_login(client)
    client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD})
    color = f"--tema-vivo: {personaje['tema']['vivo']};"
    for pagina in ['/dashboard', '/vision/', '/motivacion/', '/metodos/', '/estadisticas/']:
        assert color in client.get(pagina).get_data(as_text=True), pagina


def test_sin_sesion_no_hay_tema_del_sitio(client):
    assert '--tema-grad-1-rgb' not in client.get('/offline').get_data(as_text=True)


def test_tema_del_sitio_con_indice_invalido():
    assert tema_del_sitio(None) is None
    assert tema_del_sitio(99) is None
    assert tema_del_sitio('2') is None
    assert tema_del_sitio(0) == PERSONAJES[0]['tema']


def test_cada_tema_trae_todas_las_claves_que_usan_los_css():
    claves = {'vivo', 'vivo-rgb', 'fuerte-rgb', 'claro-rgb', 'fondo-rgb', 'grad-1', 'grad-2',
              'grad-1-rgb', 'grad-2-rgb', 'oscuro', 'oscuro-2', 'oscuro-rgb'}
    for p in PERSONAJES:
        assert set(p['tema']) == claves


def test_luz_del_mouse_azul_en_ingles(client):
    m = client.get('/static/css/m.css').get_data(as_text=True)
    assert 'var(--cursor-rgb, var(--tema-vivo-rgb' in m  # fuera de Inglés: color del tema
    for hoja in ['ingles', 'vocabulario', 'shadowing']:
        css = client.get(f'/static/css/{hoja}.css').get_data(as_text=True)
        assert '--cursor-rgb: 77, 171, 255;' in css
        assert '--tema-vivo: #4dabff;' in css  # el menú y los botones también azules


def test_login_sin_texto_de_copyright_en_el_footer(client):
    html = client.get('/').get_data(as_text=True)
    assert 'mi aplicacion de mejoras' not in html
    assert 'Disciplina &bull; Progreso' in html or 'Disciplina • Progreso' in html  # la franja animada sigue
