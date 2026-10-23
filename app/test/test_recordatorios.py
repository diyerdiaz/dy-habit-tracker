"""Recordatorios por correo: perfil, cálculo de pendientes y envío (con SMTP falso)."""
from datetime import date, datetime, timedelta

import pytest

from app import db
from app import correo
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.recordatorios import Recordatorio, MAX_RECORDATORIOS
from app.models.users import User

HOY = date(2026, 10, 21)  # miércoles (weekday 2)


class SMTPFalso:
    """Reemplaza smtplib.SMTP: guarda los mensajes en vez de enviarlos."""
    enviados = []
    falla = False

    def __init__(self, servidor, puerto, timeout=None):
        self.servidor = servidor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, usuario, clave):
        if SMTPFalso.falla:
            raise correo.smtplib.SMTPAuthenticationError(535, b'Username and Password not accepted')

    def send_message(self, mensaje):
        SMTPFalso.enviados.append(mensaje)


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


def _habito(user, nombre, dias=None, estado='Activo'):
    h = Habit(idUser=user.idUser, habitName=nombre, habitFreq='Diario',
              habitCategory='Salud', habitState=estado)
    if dias is not None:
        h.set_dias(dias)
    db.session.add(h)
    db.session.commit()
    return h


def _marcar(user, habito, fecha=HOY):
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habito.idHabit, fecha=fecha))
    db.session.commit()


def _con_correo(user, email='yo@test.com'):
    user.email = email
    db.session.commit()
    return user


def _texto(mensaje):
    return mensaje.get_body(('plain',)).get_content()


# ── Pendientes ──

def test_pendientes_solo_los_que_tocan_hoy_y_no_estan_marcados(user):
    leer = _habito(user, 'Leer')
    _habito(user, 'Correr', dias=[0, 4])          # lunes y viernes: hoy no toca
    _habito(user, 'Pausado', estado='Inactivo')
    meditar = _habito(user, 'Meditar')
    _marcar(user, meditar)
    assert [h.habitName for h in correo.habitos_pendientes(user.idUser, HOY)] == [leer.habitName]


def test_pendientes_no_mezcla_usuarios(user, other_user):
    _habito(other_user, 'Ajeno')
    assert correo.habitos_pendientes(user.idUser, HOY) == []


# ── Envío ──

def test_envia_correo_con_los_pendientes(user, smtp):
    _con_correo(user)
    _habito(user, 'Leer')
    _habito(user, 'Tomar agua')
    assert correo.enviar_pendientes(user, HOY) is True
    assert len(smtp.enviados) == 1
    mensaje = smtp.enviados[0]
    assert mensaje['To'] == 'yo@test.com'
    assert mensaje['Subject'] == 'Te faltan 2 hábitos hoy'
    assert 'Leer' in _texto(mensaje) and 'Tomar agua' in _texto(mensaje)


def test_no_envia_si_no_hay_pendientes(user, smtp):
    _con_correo(user)
    leer = _habito(user, 'Leer')
    _marcar(user, leer)
    assert correo.enviar_pendientes(user, HOY) is False
    assert smtp.enviados == []


def test_correo_de_prueba_se_envia_aunque_no_haya_pendientes(user, smtp):
    _con_correo(user)
    assert correo.enviar_pendientes(user, HOY, prueba=True) is True
    assert 'prueba' in _texto(smtp.enviados[0])


def test_no_envia_sin_correo_configurado(user, app, monkeypatch):
    _con_correo(user)
    _habito(user, 'Leer')
    app.config['MAIL_ENABLED'] = False
    monkeypatch.setattr(correo.smtplib, 'SMTP', lambda *a, **k: pytest.fail('no debía conectarse'))
    assert correo.enviar_pendientes(user, HOY) is False


def test_nombre_del_habito_se_escapa_en_el_html(user, smtp):
    _con_correo(user)
    _habito(user, '<script>x</script>')
    correo.enviar_pendientes(user, HOY)
    html = smtp.enviados[0].get_body(('html',)).get_content()
    assert '<script>x' not in html and '&lt;script&gt;' in html


# ── Programación por hora ──

def _recordatorio(user, hora, ultimo=None):
    rec = Recordatorio(idUser=user.idUser, hora=hora, ultimoEnvio=ultimo)
    db.session.add(rec)
    db.session.commit()
    return rec


def test_toca_enviar_respeta_la_hora_y_la_ventana(user):
    rec = _recordatorio(user, '20:00')
    en = lambda h, m: datetime.combine(HOY, datetime.min.time()).replace(hour=h, minute=m)
    assert not correo.toca_enviar(rec, en(19, 59))
    assert correo.toca_enviar(rec, en(20, 0))
    assert correo.toca_enviar(rec, en(20, 45))
    assert not correo.toca_enviar(rec, en(21, 0))   # fuera de la ventana de 60 min
    rec.ultimoEnvio = HOY
    assert not correo.toca_enviar(rec, en(20, 10))  # ya se envió hoy


def test_enviar_recordatorios_una_sola_vez_por_dia(user, smtp):
    _con_correo(user)
    _habito(user, 'Leer')
    rec = _recordatorio(user, '08:00')
    a_las_8 = datetime.combine(HOY, datetime.min.time()).replace(hour=8, minute=5)
    assert correo.enviar_recordatorios(a_las_8) == 1
    assert correo.enviar_recordatorios(a_las_8 + timedelta(minutes=10)) == 0
    assert len(smtp.enviados) == 1
    assert db.session.get(Recordatorio, rec.idRecordatorio).ultimoEnvio == HOY


def test_enviar_recordatorios_ignora_usuarios_sin_correo(user, smtp):
    _habito(user, 'Leer')
    _recordatorio(user, '08:00')
    a_las_8 = datetime.combine(HOY, datetime.min.time()).replace(hour=8)
    assert correo.enviar_recordatorios(a_las_8) == 0
    assert smtp.enviados == []


def test_si_falla_el_smtp_se_reintenta_despues(user, smtp):
    _con_correo(user)
    _habito(user, 'Leer')
    rec = _recordatorio(user, '08:00')
    a_las_8 = datetime.combine(HOY, datetime.min.time()).replace(hour=8)
    smtp.falla = True
    assert correo.enviar_recordatorios(a_las_8) == 0
    assert db.session.get(Recordatorio, rec.idRecordatorio).ultimoEnvio is None
    smtp.falla = False
    assert correo.enviar_recordatorios(a_las_8 + timedelta(minutes=5)) == 1


def test_comando_cli(app, user, smtp):
    resultado = app.test_cli_runner().invoke(args=['enviar-recordatorios'])
    assert resultado.exit_code == 0
    assert 'Correos enviados' in resultado.output


# ── Perfil ──

def _usuario(user):
    db.session.expire_all()
    return db.session.get(User, user.idUser)


def test_perfil_muestra_seccion_recordatorios(logged_client):
    html = logged_client.get('/perfil/').get_data(as_text=True)
    assert 'Recordatorios por correo' in html


def test_guardar_y_quitar_correo(logged_client, user):
    logged_client.post('/perfil/correo', data={'email': ' Yo@Test.com '})
    assert _usuario(user).email == 'yo@test.com'
    logged_client.post('/perfil/correo', data={'email': ''})
    assert _usuario(user).email is None


def test_correo_invalido_no_se_guarda(logged_client, user):
    logged_client.post('/perfil/correo', data={'email': 'no-es-un-correo'})
    assert _usuario(user).email is None


def test_agregar_y_borrar_recordatorio(logged_client, user):
    logged_client.post('/perfil/recordatorios', data={'hora': '20:30'})
    recs = Recordatorio.query.filter_by(idUser=user.idUser).all()
    assert [r.hora for r in recs] == ['20:30']
    assert '8:30 p. m.' in logged_client.get('/perfil/').get_data(as_text=True)
    logged_client.post(f'/perfil/recordatorios/{recs[0].idRecordatorio}/borrar')
    assert Recordatorio.query.filter_by(idUser=user.idUser).count() == 0


def test_recordatorio_hora_invalida_repetida_o_de_mas(logged_client, user):
    logged_client.post('/perfil/recordatorios', data={'hora': '25:00'})
    logged_client.post('/perfil/recordatorios', data={'hora': '07:00'})
    logged_client.post('/perfil/recordatorios', data={'hora': '07:00'})
    assert Recordatorio.query.filter_by(idUser=user.idUser).count() == 1
    for h in range(MAX_RECORDATORIOS + 2):
        logged_client.post('/perfil/recordatorios', data={'hora': f'1{h}:00'})
    assert Recordatorio.query.filter_by(idUser=user.idUser).count() == MAX_RECORDATORIOS


def test_no_puede_borrar_recordatorio_ajeno(logged_client, other_user):
    ajeno = _recordatorio(other_user, '09:00')
    respuesta = logged_client.post(f'/perfil/recordatorios/{ajeno.idRecordatorio}/borrar')
    assert respuesta.status_code == 404
    assert db.session.get(Recordatorio, ajeno.idRecordatorio) is not None


def test_boton_correo_de_prueba(logged_client, user, smtp):
    _con_correo(user)
    respuesta = logged_client.post('/perfil/correo/prueba', follow_redirects=True)
    assert len(smtp.enviados) == 1
    assert 'correo de prueba' in respuesta.get_data(as_text=True)


def test_rutas_de_recordatorios_requieren_login(client):
    for url in ('/perfil/correo', '/perfil/recordatorios', '/perfil/correo/prueba'):
        assert client.post(url).status_code == 302


# ── Diseño: personaje y racha ──

def _html(mensaje):
    return mensaje.get_body(('html',)).get_content()


def test_correo_trae_el_personaje_incrustado_con_sus_colores(user, smtp):
    from app.models.personajes_login import PERSONAJES
    _con_correo(user)
    _habito(user, 'Leer')
    correo.enviar_pendientes(user, HOY, personaje=3)
    mensaje = smtp.enviados[0]
    imagenes = [p for p in mensaje.walk() if p.get_content_maintype() == 'image']
    assert len(imagenes) == 1
    assert imagenes[0]['Content-ID'] == '<personaje>'
    assert imagenes[0].get_content()[:2] == b'\xff\xd8'  # JPG
    html = _html(mensaje)
    assert 'cid:personaje' in html
    assert PERSONAJES[3]['tema']['vivo'] in html


def test_hay_imagen_de_correo_para_cada_personaje(app):
    from app.models.personajes_login import PERSONAJES
    for i in range(len(PERSONAJES)):
        assert correo.imagen_personaje(i)[:2] == b'\xff\xd8'


def test_avisa_si_la_racha_esta_en_riesgo(user, smtp, monkeypatch):
    monkeypatch.setattr(correo, 'calcular_racha', lambda idUser: (12, 12))
    _con_correo(user)
    _habito(user, 'Leer')
    correo.enviar_pendientes(user, HOY)
    mensaje = smtp.enviados[0]
    assert 'no pierdas tu racha de 12 días' in mensaje['Subject']
    assert 'Llevas 12 días de racha' in _html(mensaje)
    assert 'para no perderla' in _texto(mensaje)


def test_racha_a_salvo_si_ya_marco_algo_hoy(user, smtp, monkeypatch):
    monkeypatch.setattr(correo, 'calcular_racha', lambda idUser: (5, 5))
    _con_correo(user)
    leer = _habito(user, 'Leer')
    _habito(user, 'Correr')
    _marcar(user, leer)
    correo.enviar_pendientes(user, HOY)
    mensaje = smtp.enviados[0]
    assert 'racha' not in mensaje['Subject']
    assert 'está a salvo hoy' in _html(mensaje)


def test_boton_solo_con_app_url(user, smtp, app):
    _con_correo(user)
    _habito(user, 'Leer')
    correo.enviar_pendientes(user, HOY)
    assert 'Marcar mis hábitos' not in _html(smtp.enviados[0])
    app.config['APP_URL'] = 'https://habits.ejemplo.com/'
    correo.enviar_pendientes(user, HOY)
    html = _html(smtp.enviados[1])
    assert 'href="https://habits.ejemplo.com/habitos/check"' in html
    assert 'https://habits.ejemplo.com/perfil/#recordatorios' in html


def test_asunto_de_prueba(user, smtp):
    _con_correo(user)
    correo.enviar_pendientes(user, HOY, prueba=True)
    assert smtp.enviados[0]['Subject'].startswith('Prueba:')
