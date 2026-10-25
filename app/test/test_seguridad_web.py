"""Seguridad del despliegue y de las sesiones: puerto cerrado, cabeceras,
bloqueo de login por IP, recuperar sin revelar cuentas, logout por POST y
cierre de sesiones al cambiar la contraseña."""
import re
from pathlib import Path

import pytest

from app import create_app, db
from app.models.intentos_login import IntentoLogin, MAX_FALLOS, MAX_FALLOS_POR_IP
from app.models.users import User
from app.test.conftest import TEST_PASSWORD

RAIZ = Path(__file__).resolve().parent.parent.parent
IP_A, IP_B = '203.0.113.10', '198.51.100.20'


def _entrar(client, usuario='test_user', clave=TEST_PASSWORD, ip=IP_A):
    return client.post('/', data={'nameUser': usuario, 'passwordUser': clave},
                       environ_base={'REMOTE_ADDR': ip}, follow_redirects=True)


# ── 1. Puerto de gunicorn cerrado ──

def test_compose_no_publica_el_puerto_de_gunicorn():
    compose = (RAIZ / 'docker-compose.yml').read_text()
    assert not re.search(r'^\s*ports:', compose, re.M)
    assert '4000:4000' not in compose
    assert re.search(r'expose:\s*\n\s*- "4000"', compose)
    # Detrás del Traefik de Coolify: un solo proxy de confianza
    assert 'PROXIES_DE_CONFIANZA: "1"' in compose


# ── 2. Cabeceras de seguridad ──

CABECERAS = {
    'Strict-Transport-Security': 'max-age=31536000',
    'X-Frame-Options': 'DENY',
    'Content-Security-Policy': "frame-ancestors 'none'",
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
}


@pytest.mark.parametrize('url', ['/', '/recuperar/', '/no-existe', '/static/css/m.css', '/sw.js'])
def test_cabeceras_de_seguridad_en_todas_las_respuestas(client, url):
    respuesta = client.get(url)
    for nombre, valor in CABECERAS.items():
        assert respuesta.headers.get(nombre) == valor, (url, nombre)
    respuesta.close()


def test_cabeceras_tambien_con_sesion_y_en_json(logged_client):
    for respuesta in (logged_client.get('/dashboard'),
                      logged_client.post('/metodos/tarjetas/999/mover', json={})):
        for nombre, valor in CABECERAS.items():
            assert respuesta.headers.get(nombre) == valor, nombre


def test_hsts_no_incluye_subdominios(client):
    # Otros subdominios (como el panel de Coolify) podrían no tener HTTPS todavía
    assert 'includeSubDomains' not in client.get('/').headers['Strict-Transport-Security']


# ── 3. Bloqueo de login por IP ──

def test_el_atacante_no_bloquea_al_dueno_de_la_cuenta(app, user):
    atacante, dueno = app.test_client(), app.test_client()
    for _ in range(MAX_FALLOS):
        _entrar(atacante, clave='mala', ip=IP_A)
    assert 'Demasiados intentos' in _entrar(atacante, ip=IP_A).get_data(as_text=True)
    # Desde otra IP el dueño entra con su contraseña sin problema
    respuesta = _entrar(dueno, ip=IP_B)
    assert respuesta.request.path == '/dashboard'


def test_el_bloqueo_por_usuario_e_ip_sigue_funcionando(app, user):
    cliente = app.test_client()
    for _ in range(MAX_FALLOS):
        _entrar(cliente, clave='mala', ip=IP_A)
    # Aunque ahora escriba la contraseña correcta, desde esa IP espera
    assert _entrar(cliente, ip=IP_A).request.path == '/'
    assert IntentoLogin.minutos_bloqueado('test_user', IP_A) > 0
    assert IntentoLogin.minutos_bloqueado('test_user', IP_B) == 0


def test_tope_por_ip_aunque_cambie_de_usuario(app, user):
    cliente = app.test_client()
    # Menos de 6 fallos por usuario, pero muchos en total desde la misma IP
    for i in range(MAX_FALLOS_POR_IP):
        _entrar(cliente, usuario=f'victima{i // 4}', clave='mala', ip=IP_A)
    assert IntentoLogin.minutos_bloqueado('otro_usuario_nuevo', IP_A) > 0
    assert 'Demasiados intentos' in _entrar(cliente, ip=IP_A).get_data(as_text=True)
    assert _entrar(app.test_client(), ip=IP_B).request.path == '/dashboard'


def test_entrar_bien_no_borra_el_tope_de_la_ip(app, user):
    cliente = app.test_client()
    for i in range(MAX_FALLOS_POR_IP - 1):
        _entrar(cliente, usuario=f'victima{i // 4}', clave='mala', ip=IP_A)
    _entrar(cliente, ip=IP_A)              # entra a su propia cuenta...
    cliente.post('/logout')
    _entrar(cliente, usuario='victima99', clave='mala', ip=IP_A)
    assert IntentoLogin.minutos_bloqueado('cualquiera', IP_A) > 0   # ...y aun así se bloquea


def test_ip_real_detras_del_proxy():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                      'WTF_CSRF_ENABLED': False, 'SECRET_KEY': 'x', 'PROXIES_DE_CONFIANZA': 1})
    with app.app_context():
        db.create_all()
        app.test_client().post('/', data={'nameUser': 'x', 'passwordUser': 'mala'},
                               headers={'X-Forwarded-For': IP_B}, environ_base={'REMOTE_ADDR': '10.0.0.2'})
        assert db.session.get(IntentoLogin, ('x', IP_B)) is not None
        db.drop_all()


def test_sin_proxy_no_se_cree_la_cabecera_falsa(client):
    # En local (sin proxy) alguien podría inventarse X-Forwarded-For para esquivar el bloqueo
    client.post('/', data={'nameUser': 'x', 'passwordUser': 'mala'},
                headers={'X-Forwarded-For': IP_B}, environ_base={'REMOTE_ADDR': IP_A})
    assert db.session.get(IntentoLogin, ('x', IP_A)) is not None
    assert db.session.get(IntentoLogin, ('x', IP_B)) is None


# ── 4. Recuperar sin revelar cuentas (detalle en test_recuperar_contrasena.py) ──

def test_recuperar_responde_igual_para_cuentas_reales_y_falsas(app, user):
    app.config['MAIL_ENABLED'] = True
    user.email = 'dueno@test.com'
    db.session.commit()
    textos = []
    for identificador in ('test_user', 'no_existe', 'dueno@test.com', 'nadie@test.com'):
        respuesta = app.test_client().post('/recuperar/', data={'identificador': identificador},
                                           follow_redirects=False)
        textos.append((respuesta.status_code, respuesta.headers.get('Location')))
    assert len(set(textos)) == 1 and textos[0] == (302, '/recuperar/codigo')


# ── 5. Logout solo por POST ──

def test_logout_por_get_no_cierra_la_sesion(logged_client):
    assert logged_client.get('/logout').status_code == 405
    assert logged_client.get('/dashboard').status_code == 200   # sigue dentro


def test_logout_por_post_cierra_la_sesion(logged_client):
    respuesta = logged_client.post('/logout')
    assert respuesta.status_code == 302
    assert logged_client.get('/dashboard').status_code == 302   # ya no entra


def test_ninguna_plantilla_cierra_sesion_con_un_enlace():
    plantillas = list((RAIZ / 'app' / 'templates').rglob('*.html'))
    con_logout = [p for p in plantillas if "auth.logout" in p.read_text()]
    assert len(con_logout) >= 20
    for p in con_logout:
        texto = p.read_text()
        assert not re.search(r'<a [^>]*auth\.logout', texto), p.name
        for form in re.findall(r'<form[^>]*auth\.logout[^>]*>.*?</form>', texto, re.S):
            assert 'method="post"' in form and 'name="csrf_token"' in form, p.name


def test_logout_exige_token_csrf():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'SECRET_KEY': 'x'})
    with app.app_context():
        db.create_all()
        db.session.add(User(nameUser='u', password='Clave_123'))
        db.session.commit()
        cliente = app.test_client()
        html = cliente.get('/').get_data(as_text=True)
        token = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
        cliente.post('/', data={'nameUser': 'u', 'passwordUser': 'Clave_123', 'csrf_token': token})
        # Otra página no puede cerrarte la sesión: sin token se rechaza
        assert cliente.post('/logout').status_code in (302, 400)
        assert cliente.get('/dashboard').status_code == 200
        dashboard = cliente.get('/dashboard').get_data(as_text=True)
        token = re.search(r'name="csrf-token" content="([^"]+)"', dashboard).group(1)
        cliente.post('/logout', data={'csrf_token': token})
        assert cliente.get('/dashboard').status_code == 302
        db.drop_all()


# ── 6. Cambiar la contraseña cierra las demás sesiones ──

NUEVA = 'Clave_nueva_456'


def _cambiar_en_perfil(cliente):
    return cliente.post('/perfil/contrasena', data={
        'contrasena_actual': TEST_PASSWORD, 'nueva_contrasena': NUEVA, 'confirmar_contrasena': NUEVA,
    }, follow_redirects=True)


def test_cambiar_contrasena_cierra_las_otras_sesiones(app, user):
    pc, celular = app.test_client(), app.test_client()
    _entrar(pc, ip=IP_A)
    _entrar(celular, ip=IP_B)
    assert 'Se cerraron tus otras sesiones' in _cambiar_en_perfil(pc).get_data(as_text=True)

    assert pc.get('/dashboard').status_code == 200          # quien la cambió sigue dentro
    respuesta = celular.get('/dashboard', follow_redirects=True)
    assert respuesta.request.path == '/'                     # la otra sesión se cerró
    assert 'Tu contraseña cambió' in respuesta.get_data(as_text=True)
    assert celular.get('/dashboard').status_code == 302      # y no vuelve a entrar sola
    assert _entrar(celular, clave=NUEVA, ip=IP_B).request.path == '/dashboard'


def test_peticiones_fetch_de_una_sesion_cerrada_reciben_401(app, user):
    pc, celular = app.test_client(), app.test_client()
    _entrar(pc, ip=IP_A)
    _entrar(celular, ip=IP_B)
    _cambiar_en_perfil(pc)
    respuesta = celular.post('/metodos/tarjetas/1/mover', json={'columna': 'hecho'})
    assert respuesta.status_code == 401 and respuesta.get_json()['success'] is False


def test_recuperar_la_contrasena_cierra_todas_las_sesiones(app, user):
    sesion_abierta = app.test_client()
    _entrar(sesion_abierta, ip=IP_A)
    user = db.session.get(User, user.idUser)
    version = user.sesionVersion
    user.cambiar_contrasena(NUEVA)   # lo mismo que hace /recuperar/nueva
    db.session.commit()
    assert user.sesionVersion == version + 1
    assert sesion_abierta.get('/dashboard').status_code == 302


def test_sesiones_de_antes_del_cambio_siguen_validas(app, user):
    # Quien ya tenía la sesión abierta al desplegar esto no debe ser expulsado
    cliente = app.test_client()
    _entrar(cliente)
    with cliente.session_transaction() as sesion:
        sesion.pop('sesion_version')
    assert cliente.get('/dashboard').status_code == 200


def test_crear_cuenta_o_migrar_clave_vieja_no_cuenta_como_cambio(app):
    nuevo = User(nameUser='nuevo', password='Clave_123')
    db.session.add(nuevo)
    db.session.commit()
    assert nuevo.sesionVersion == 0


def test_esquema_agrega_la_columna_en_bases_existentes():
    texto = (RAIZ / 'app' / '__init__.py').read_text()
    assert "'sesionVersion': 'INTEGER NOT NULL DEFAULT 0'" in texto
