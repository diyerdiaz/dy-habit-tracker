"""Recuperar la contraseña con un código de 6 dígitos por correo (SMTP falso)."""
import re
from datetime import datetime, timedelta

import pytest

from app import db, correo
from app.models.codigos_recuperacion import CodigoRecuperacion
from app.models.users import User
from app.test.conftest import TEST_PASSWORD
from app.test.test_recordatorios import SMTPFalso


@pytest.fixture
def smtp(app, monkeypatch):
    SMTPFalso.enviados = []
    SMTPFalso.falla = False
    monkeypatch.setattr(correo.smtplib, 'SMTP', SMTPFalso)
    app.config.update(
        MAIL_ENABLED=True, MAIL_SERVER='smtp.test', MAIL_PORT=587,
        MAIL_USERNAME='app@test.com', MAIL_PASSWORD='clave', MAIL_FROM='app@test.com',
    )
    return SMTPFalso


@pytest.fixture
def con_correo(user):
    user.email = 'diyer@test.com'
    db.session.commit()
    return user


def _pedir(client, identificador='test_user'):
    return client.post('/recuperar/', data={'identificador': identificador}, follow_redirects=True)


def _codigo_enviado(smtp):
    return re.search(r'\b(\d{6})\b', smtp.enviados[-1]['Subject']).group(1)


def _escribir(client, codigo):
    return client.post('/recuperar/codigo', data={'codigo': codigo}, follow_redirects=True)


def _cambiar(client, clave='Clave_nueva_123', confirmar=None):
    return client.post('/recuperar/nueva', data={
        'nueva_contrasena': clave, 'confirmar_contrasena': confirmar or clave,
    }, follow_redirects=True)


def _usuario(user):
    db.session.expire_all()
    return db.session.get(User, user.idUser)


def _otro_codigo_permitido(user):
    # Simula que pasó el minuto de espera entre códigos
    for r in CodigoRecuperacion.query.filter_by(idUser=user.idUser).all():
        r.createdAt -= timedelta(minutes=2)
    db.session.commit()


# ── Paso 1: usuario o correo ──

def test_login_muestra_enlace_para_recuperar(client):
    html = client.get('/').get_data(as_text=True)
    assert '¿Olvidaste tu contraseña?' in html and '/recuperar/' in html


def test_pantalla_de_recuperar(client):
    html = client.get('/recuperar/').get_data(as_text=True)
    assert 'Usuario o correo electrónico' in html


def test_cuenta_que_no_existe_no_deja_seguir(client, smtp):
    html = _pedir(client, 'no_existe').get_data(as_text=True)
    assert 'No encontramos ninguna cuenta' in html
    assert smtp.enviados == []


def test_cuenta_sin_correo_no_se_puede_recuperar(client, user, smtp):
    html = _pedir(client).get_data(as_text=True)
    assert 'no tiene un correo registrado' in html
    assert smtp.enviados == []


def test_por_usuario_envia_el_codigo(client, con_correo, smtp):
    respuesta = _pedir(client)
    html = respuesta.get_data(as_text=True)
    assert respuesta.request.path == '/recuperar/codigo'
    assert len(smtp.enviados) == 1
    assert smtp.enviados[0]['To'] == 'diyer@test.com'
    assert 'd***er@test.com' in html          # el correo se muestra oculto
    assert 'diyer@test.com' not in html


def test_por_correo_sin_importar_mayusculas(client, con_correo, smtp):
    _pedir(client, 'DIYER@Test.com')
    assert len(smtp.enviados) == 1


def test_correo_repetido_en_varias_cuentas_pide_usuario(client, con_correo, other_user, smtp):
    other_user.email = 'diyer@test.com'
    db.session.commit()
    html = _pedir(client, 'diyer@test.com').get_data(as_text=True)
    assert 'varias cuentas' in html
    assert smtp.enviados == []


def test_correo_del_codigo_trae_codigo_y_personaje(client, con_correo, smtp):
    _pedir(client)
    mensaje = smtp.enviados[0]
    codigo = _codigo_enviado(smtp)
    assert codigo in mensaje.get_body(('plain',)).get_content()
    assert codigo in mensaje.get_body(('html',)).get_content()
    assert any(p['Content-ID'] == '<personaje>' for p in mensaje.walk())


def test_el_codigo_se_guarda_como_hash(client, con_correo, smtp):
    _pedir(client)
    registro = CodigoRecuperacion.query.one()
    assert _codigo_enviado(smtp) not in registro.codigoHash


# ── Paso 2: el código ──

def test_codigo_correcto_lleva_a_nueva_contrasena(client, con_correo, smtp):
    _pedir(client)
    respuesta = _escribir(client, _codigo_enviado(smtp))
    assert respuesta.request.path == '/recuperar/nueva'


def test_codigo_incorrecto_descuenta_intentos(client, con_correo, smtp):
    _pedir(client)
    html = _escribir(client, '000000' if _codigo_enviado(smtp) != '000000' else '111111').get_data(as_text=True)
    assert 'Te quedan 2 intentos' in html


def test_tres_intentos_fallidos_anulan_el_codigo(client, con_correo, smtp):
    _pedir(client)
    bueno = _codigo_enviado(smtp)
    malo = '000000' if bueno != '000000' else '111111'
    _escribir(client, malo)
    _escribir(client, malo)
    html = _escribir(client, malo).get_data(as_text=True)
    assert 'Usaste los 3 intentos' in html
    # Ni siquiera el código correcto sirve ya
    respuesta = _escribir(client, bueno)
    assert respuesta.request.path == '/recuperar/codigo'
    assert 'Ya no tienes un código válido' in respuesta.get_data(as_text=True)


def test_codigo_vence_a_los_5_minutos(client, con_correo, smtp):
    _pedir(client)
    registro = CodigoRecuperacion.query.one()
    assert registro.expira - registro.createdAt == timedelta(minutes=5)
    registro.expira = datetime.now() - timedelta(seconds=1)
    db.session.commit()
    respuesta = _escribir(client, _codigo_enviado(smtp))
    assert respuesta.request.path == '/recuperar/codigo'
    assert 'venció' in respuesta.get_data(as_text=True)


def test_pantalla_del_codigo_muestra_tiempo_e_intentos(client, con_correo, smtp):
    html = _pedir(client).get_data(as_text=True)
    assert 'data-segundos=' in html and '3 intentos' in html


def test_sin_pedir_codigo_no_entra_al_paso_2_ni_3(client):
    assert client.get('/recuperar/codigo').headers['Location'].endswith('/recuperar/')
    assert client.get('/recuperar/nueva').headers['Location'].endswith('/recuperar/')


def test_paso_3_exige_haber_verificado_el_codigo(client, con_correo, smtp):
    _pedir(client)
    respuesta = client.get('/recuperar/nueva')
    assert respuesta.headers['Location'].endswith('/recuperar/codigo')


# ── Reenviar y límites ──

def test_reenviar_anula_el_codigo_anterior(client, con_correo, smtp):
    _pedir(client)
    viejo = _codigo_enviado(smtp)
    _otro_codigo_permitido(con_correo)
    client.post('/recuperar/reenviar')
    nuevo = _codigo_enviado(smtp)
    assert len(smtp.enviados) == 2
    if viejo != nuevo:
        assert _escribir(client, viejo).request.path == '/recuperar/codigo'
    assert _escribir(client, nuevo).request.path == '/recuperar/nueva'


def test_un_codigo_por_minuto(client, con_correo, smtp):
    _pedir(client)
    html = client.post('/recuperar/reenviar', follow_redirects=True).get_data(as_text=True)
    assert len(smtp.enviados) == 1
    assert 'Espera un minuto' in html


def test_maximo_5_codigos_al_dia(client, con_correo, smtp):
    for _ in range(correo.CODIGO_MAX_DIA_USUARIO):
        _pedir(client)
        _otro_codigo_permitido(con_correo)
    html = _pedir(client).get_data(as_text=True)
    assert len(smtp.enviados) == correo.CODIGO_MAX_DIA_USUARIO
    assert 'Inténtalo mañana' in html


def test_sin_correo_configurado_en_el_servidor(client, con_correo, app):
    app.config['MAIL_ENABLED'] = False
    html = _pedir(client).get_data(as_text=True)
    assert 'no está disponible' in html
    assert CodigoRecuperacion.query.count() == 0


def test_si_falla_el_smtp_el_codigo_queda_anulado(client, con_correo, smtp):
    smtp.falla = True
    html = _pedir(client).get_data(as_text=True)
    assert 'No se pudo enviar el correo' in html
    assert CodigoRecuperacion.query.one().anulado is True


# ── Paso 3: contraseña nueva ──

def _hasta_paso_3(client, smtp):
    _pedir(client)
    _escribir(client, _codigo_enviado(smtp))


def test_cambia_la_contrasena_y_avisa_por_correo(client, con_correo, smtp):
    _hasta_paso_3(client, smtp)
    respuesta = _cambiar(client)
    assert respuesta.request.path == '/'
    assert 'Tu contraseña se cambió' in respuesta.get_data(as_text=True)
    u = _usuario(con_correo)
    assert u.check_password('Clave_nueva_123')
    assert not u.check_password(TEST_PASSWORD)
    assert smtp.enviados[-1]['Subject'] == 'Tu contraseña se cambió'
    # Con la nueva se puede entrar
    login = client.post('/', data={'nameUser': 'test_user', 'passwordUser': 'Clave_nueva_123'}, follow_redirects=True)
    assert login.request.path == '/dashboard'


def test_el_codigo_sirve_una_sola_vez(client, con_correo, smtp):
    _hasta_paso_3(client, smtp)
    _cambiar(client)
    assert client.get('/recuperar/nueva').status_code == 302
    assert _cambiar(client, 'Otra_clave_456').request.path != '/'
    assert _usuario(con_correo).check_password('Clave_nueva_123')


def test_contrasena_corta_o_distinta_no_se_guarda(client, con_correo, smtp):
    _hasta_paso_3(client, smtp)
    assert 'no es segura' in _cambiar(client, 'corta').get_data(as_text=True)
    assert 'no coinciden' in _cambiar(client, 'Clave_nueva_123', 'Otra_cosa_123').get_data(as_text=True)
    assert _usuario(con_correo).check_password(TEST_PASSWORD)


def test_tiempo_limite_para_cambiar_tras_verificar(client, con_correo, smtp):
    _hasta_paso_3(client, smtp)
    registro = CodigoRecuperacion.query.one()
    registro.verificadoAt = datetime.now() - timedelta(minutes=11)
    db.session.commit()
    assert client.get('/recuperar/nueva').status_code == 302
    assert _usuario(con_correo).check_password(TEST_PASSWORD)


def test_usuario_con_sesion_va_a_su_perfil(logged_client):
    assert logged_client.get('/recuperar/').headers['Location'].endswith('/perfil/')


def test_ocultar_email():
    assert correo.ocultar_email('diyerdiaz7@gmail.com') == 'd***z7@gmail.com'
    assert correo.ocultar_email('ab@x.com') == 'a***@x.com'


def test_borrar_usuario_borra_sus_codigos(app, con_correo, smtp):
    from app.routes.users_route import _delete_user_data
    CodigoRecuperacion.crear(con_correo.idUser)
    _delete_user_data(con_correo.idUser)
    db.session.commit()
    assert CodigoRecuperacion.query.count() == 0


def test_codigo_se_escribe_en_6_cuadros(client, con_correo, smtp):
    html = _pedir(client).get_data(as_text=True)
    assert html.count('class="codigo-caja"') == 6
    # Los cuadros no se envían solos: recuperar.js junta los dígitos en el campo oculto
    assert '<input type="hidden" name="codigo" id="codigo">' in html
    assert 'autocomplete="one-time-code"' in html
    assert 'js/recuperar.js' in html


def test_titulo_largo_no_descuadra_la_tarjeta(client):
    css = client.get('/static/css/login.css').get_data(as_text=True)
    assert 'grid-template-columns: minmax(0, 1fr)' in css


def test_aviso_de_contrasena_cambiada_con_diseno(client, con_correo, smtp):
    _hasta_paso_3(client, smtp)
    _cambiar(client)
    aviso = smtp.enviados[-1]
    assert aviso['Subject'] == 'Tu contraseña se cambió'
    html = aviso.get_body(('html',)).get_content()
    assert 'cid:personaje' in html and '¿No fuiste tú?' in html
    assert any(p['Content-ID'] == '<personaje>' for p in aviso.walk())
    assert 'código de recuperación' in aviso.get_body(('plain',)).get_content()


def test_el_codigo_nunca_aparece_en_la_web(client, con_correo, smtp):
    """El código solo viaja en el correo: ni en las páginas, ni en la URL, ni en la sesión."""
    paginas = [_pedir(client)]
    codigo = _codigo_enviado(smtp)
    paginas.append(client.get('/recuperar/codigo'))
    paginas.append(_escribir(client, codigo))
    for respuesta in paginas:
        assert codigo not in respuesta.get_data(as_text=True)
        assert codigo not in respuesta.request.url
    with client.session_transaction() as sesion:
        assert codigo not in str(dict(sesion))


def test_los_codigos_son_aleatorios(con_correo):
    codigos = {CodigoRecuperacion.crear(con_correo.idUser)[1] for _ in range(30)}
    assert len(codigos) > 25
    assert all(len(c) == 6 and c.isdigit() for c in codigos)
