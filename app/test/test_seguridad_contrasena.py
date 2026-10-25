"""Seguridad de las contraseñas: requisitos, bloqueo del login y cambio obligatorio."""
from datetime import datetime, timedelta

import pytest

from app import db
from app.models.intentos_login import IntentoLogin, MAX_FALLOS, MINUTOS_BLOQUEO

IP = '127.0.0.1'  # la del cliente de pruebas de Flask
from app.models.users import User, contrasena_segura, requisitos_faltantes, mensaje_requisitos
from app.test.conftest import TEST_PASSWORD

CLAVE_DEBIL = 'clave123'           # sin mayúscula ni símbolo (como las cuentas antiguas)
CLAVE_SEGURA = 'Nueva_clave_2026'


def _entrar(client, usuario='test_user', clave=TEST_PASSWORD):
    return client.post('/', data={'nameUser': usuario, 'passwordUser': clave}, follow_redirects=True)


def _usuario(nombre):
    db.session.expire_all()
    return User.query.filter_by(nameUser=nombre).first()


# ── Requisitos ──

@pytest.mark.parametrize('clave, falta', [
    ('Ab1!', 'Mínimo 8 caracteres'),
    ('abcdefg1!', 'Una letra mayúscula'),
    ('ABCDEFG1!', 'Una letra minúscula'),
    ('Abcdefgh!', 'Un número'),
    ('Abcdefgh1', 'Un símbolo (por ejemplo ! @ # $ . _ -)'),
])
def test_cada_requisito(clave, falta):
    assert falta in requisitos_faltantes(clave)
    assert not contrasena_segura(clave)


def test_contrasena_que_cumple_todo():
    assert requisitos_faltantes(CLAVE_SEGURA) == []
    assert contrasena_segura(CLAVE_SEGURA)
    assert contrasena_segura('Ñandú_2026')        # letras con tilde también cuentan
    assert mensaje_requisitos(CLAVE_SEGURA) is None


def test_mensaje_dice_lo_que_falta():
    assert mensaje_requisitos('abc') == ('La contraseña no es segura. Le falta: mínimo 8 caracteres, '
                                         'una letra mayúscula, un número, un símbolo (por ejemplo ! @ # $ . _ -).')
    assert 'máximo 128' in mensaje_requisitos('Aa1!' * 40)


def test_registro_exige_contrasena_segura(client):
    client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': CLAVE_DEBIL})
    assert _usuario('nuevo') is None
    client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': CLAVE_SEGURA})
    assert _usuario('nuevo') is not None


def test_perfil_exige_contrasena_segura(logged_client, user):
    for nueva in (CLAVE_DEBIL, CLAVE_SEGURA):
        logged_client.post('/perfil/contrasena', data={
            'contrasena_actual': TEST_PASSWORD,
            'nueva_contrasena': nueva, 'confirmar_contrasena': nueva,
        })
        if nueva == CLAVE_DEBIL:
            assert _usuario('test_user').check_password(TEST_PASSWORD)
    assert _usuario('test_user').check_password(CLAVE_SEGURA)


def test_pantallas_muestran_los_requisitos(client, user):
    assert 'requisitos-contrasena' in client.get('/').get_data(as_text=True)          # registro
    _entrar(client)
    assert 'requisitos-contrasena' in client.get('/perfil/').get_data(as_text=True)
    assert client.get('/static/js/contrasena.js').status_code == 200
    assert client.get('/static/css/contrasena.css').status_code == 200


# ── Bloqueo del login ──

def test_avisa_intentos_restantes(client, user):
    html = _entrar(client, clave='mala').get_data(as_text=True)
    assert f'Te quedan {MAX_FALLOS - 1} intentos' in html


def test_seis_fallos_bloquean_30_minutos(client, user):
    for _ in range(MAX_FALLOS - 1):
        _entrar(client, clave='mala')
    html = _entrar(client, clave='mala').get_data(as_text=True)
    assert f'bloqueado {MINUTOS_BLOQUEO} minutos' in html
    # Bloqueado: ni con la contraseña correcta entra
    respuesta = _entrar(client)
    assert respuesta.request.path == '/'
    assert 'Demasiados intentos fallidos' in respuesta.get_data(as_text=True)
    assert IntentoLogin.minutos_bloqueado('test_user', IP) == MINUTOS_BLOQUEO


def test_tras_los_30_minutos_puede_entrar(client, user):
    for _ in range(MAX_FALLOS):
        _entrar(client, clave='mala')
    registro = db.session.get(IntentoLogin, ('test_user', IP))
    registro.bloqueadoHasta = datetime.now() - timedelta(seconds=1)
    db.session.commit()
    assert _entrar(client).request.path == '/dashboard'


def test_entrar_bien_reinicia_el_contador(client, user):
    for _ in range(MAX_FALLOS - 1):
        _entrar(client, clave='mala')
    assert _entrar(client).request.path == '/dashboard'
    client.post('/logout')
    html = _entrar(client, clave='mala').get_data(as_text=True)
    assert f'Te quedan {MAX_FALLOS - 1} intentos' in html


def test_fallos_viejos_se_olvidan(client, user):
    for _ in range(MAX_FALLOS - 1):
        _entrar(client, clave='mala')
    registro = db.session.get(IntentoLogin, ('test_user', IP))
    registro.actualizado = datetime.now() - timedelta(minutes=31)
    db.session.commit()
    html = _entrar(client, clave='mala').get_data(as_text=True)
    assert f'Te quedan {MAX_FALLOS - 1} intentos' in html


def test_bloqueo_tambien_para_usuarios_que_no_existen(client):
    # Mismo comportamiento: el bloqueo no revela si la cuenta existe
    for _ in range(MAX_FALLOS):
        _entrar(client, usuario='no_existe', clave='mala')
    assert IntentoLogin.minutos_bloqueado('no_existe', IP) > 0


def test_bloquear_un_usuario_no_afecta_a_otro(client, user, other_user):
    for _ in range(MAX_FALLOS):
        _entrar(client, clave='mala')
    assert _entrar(client, usuario='otro', clave='Otra_clave1').request.path == '/dashboard'


def test_recuperar_la_contrasena_quita_el_bloqueo(client, user):
    for _ in range(MAX_FALLOS):
        _entrar(client, clave='mala')
    IntentoLogin.limpiar_usuario('test_user')
    assert IntentoLogin.minutos_bloqueado('test_user', IP) == 0


# ── Cambio obligatorio de contraseñas antiguas ──

@pytest.fixture
def usuario_debil(app):
    u = User(nameUser='antiguo', password=CLAVE_DEBIL)
    db.session.add(u)
    db.session.commit()
    return u


def test_contrasena_antigua_debil_obliga_a_cambiarla(client, usuario_debil):
    respuesta = _entrar(client, 'antiguo', CLAVE_DEBIL)
    assert respuesta.request.path == '/perfil/actualizar-contrasena'
    html = respuesta.get_data(as_text=True)
    assert 'Actualiza tu contraseña' in html and 'requisitos-contrasena' in html
    # La contraseña no se tocó: sigue siendo la misma
    assert _usuario('antiguo').check_password(CLAVE_DEBIL)


def test_no_puede_usar_la_app_sin_cambiarla(client, usuario_debil):
    _entrar(client, 'antiguo', CLAVE_DEBIL)
    for url in ('/dashboard', '/perfil/', '/register_habit', '/estadisticas/'):
        assert client.get(url).headers['Location'].endswith('/perfil/actualizar-contrasena'), url
    # Cerrar sesión sí se permite
    assert client.post('/logout').headers['Location'].endswith('/')


def test_al_cambiarla_sigue_normal(client, usuario_debil):
    _entrar(client, 'antiguo', CLAVE_DEBIL)
    respuesta = client.post('/perfil/actualizar-contrasena', data={
        'nueva_contrasena': CLAVE_SEGURA, 'confirmar_contrasena': CLAVE_SEGURA,
    }, follow_redirects=True)
    assert respuesta.request.path == '/dashboard'
    assert _usuario('antiguo').check_password(CLAVE_SEGURA)
    assert client.get('/perfil/').status_code == 200
    # La próxima vez entra directo
    client.post('/logout')
    assert _entrar(client, 'antiguo', CLAVE_SEGURA).request.path == '/dashboard'


def test_la_nueva_tambien_debe_ser_segura_y_coincidir(client, usuario_debil):
    _entrar(client, 'antiguo', CLAVE_DEBIL)
    for nueva, confirmar, mensaje in (
        ('otra_debil', 'otra_debil', 'no es segura'),
        (CLAVE_SEGURA, 'Distinta_2026', 'no coinciden'),
    ):
        html = client.post('/perfil/actualizar-contrasena', data={
            'nueva_contrasena': nueva, 'confirmar_contrasena': confirmar,
        }, follow_redirects=True).get_data(as_text=True)
        assert mensaje in html
    assert _usuario('antiguo').check_password(CLAVE_DEBIL)


def test_contrasena_segura_entra_directo(logged_client):
    assert logged_client.get('/dashboard').status_code == 200
    assert logged_client.get('/perfil/actualizar-contrasena').headers['Location'].endswith('/dashboard')


def test_cookie_segura_en_produccion():
    from pathlib import Path
    compose = (Path(__file__).resolve().parents[2] / 'docker-compose.yml').read_text()
    assert 'SESSION_COOKIE_SECURE: "1"' in compose
