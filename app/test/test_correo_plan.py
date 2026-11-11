"""Imagen del plan del mes por correo: sale una vez al empezar el mes (cuando el
plan está confirmado), con la imagen incrustada y adjunta; si falla, se reintenta
en la próxima ejecución y nunca sale dos veces el mismo mes."""
import smtplib
from datetime import datetime
from email import message_from_bytes
from io import BytesIO

from PIL import Image

from app import db
from app.models.habitos import Habit
from app.models.plan_mensual import PlanMensual, PlanEnviado
from app.models.recordatorios import Recordatorio
from app.services import correo
from app.services.cuentas import borrar_cuenta
from app.services.imagen_plan import imagen_plan_png, plan_por_dia

AHORA = datetime(2026, 11, 1, 8, 0)
HOY = AHORA.date()


def _preparar(user, plan=True, recordatorio=True, email='persona@test.com'):
    user.email = email
    for nombre, dias, estado in (('Leer', None, 'Activo'), ('Gym', '0,2,4', 'Activo'),
                                 ('Llamar a la familia', '6', 'Activo'), ('Correr', None, 'Pausado')):
        h = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario', habitCategory='x', habitState=estado)
        h.diasSemana = dias
        db.session.add(h)
    if recordatorio:
        db.session.add(Recordatorio(idUser=user.idUser, hora='21:00'))
    if plan:
        db.session.add(PlanMensual(idUser=user.idUser, anio=HOY.year, mes=HOY.month))
    db.session.commit()


def _capturar(monkeypatch, app):
    app.config['MAIL_ENABLED'] = True
    enviados = []

    def falso(destino, asunto, texto, html=None, imagenes=None, adjuntos=None):
        enviados.append(dict(destino=destino, asunto=asunto, texto=texto, html=html,
                             imagenes=imagenes or {}, adjuntos=adjuntos or []))
        return True

    monkeypatch.setattr(correo, 'enviar_correo', falso)
    return enviados


def _planes(enviados):
    return [c for c in enviados if 'plan de hábitos' in c['asunto']]


# ── La imagen ──

def test_la_imagen_es_un_png_valido():
    png = imagen_plan_png('Ana', [('Leer', list(range(7))), ('Gym', [0, 2, 4])], 2026, 11)
    imagen = Image.open(BytesIO(png))
    assert imagen.format == 'PNG' and imagen.width == 1080
    # Más hábitos = imagen más alta
    otra = Image.open(BytesIO(imagen_plan_png('Ana', [('Leer', [0])] * 6, 2026, 11)))
    assert otra.height > imagen.height


def test_plan_por_dia():
    dias = plan_por_dia([('Leer', list(range(7))), ('Gym', [0, 2, 4]), ('Familia', [6])])
    assert dias[0] == ('Lunes', ['Leer', 'Gym'])
    assert dias[1] == ('Martes', ['Leer'])
    assert dias[6] == ('Domingo', ['Leer', 'Familia'])


def test_nombres_largos_no_rompen_la_imagen():
    png = imagen_plan_png('Ana', [('Un hábito con un nombre larguísimo que no cabe ' * 3, [1])], 2026, 2)
    assert Image.open(BytesIO(png)).width == 1080


# ── El correo ──

def test_envia_la_imagen_incrustada_y_adjunta(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_planes_mes(AHORA) == 1
    (c,) = _planes(enviados)
    assert c['destino'] == 'persona@test.com' and 'noviembre' in c['asunto']
    assert 'cid:plan' in c['html'] and c['imagenes']['plan'][1] == 'png'
    nombre, datos, tipo, subtipo = c['adjuntos'][0]
    assert nombre == 'plan-noviembre-2026.png' and (tipo, subtipo) == ('image', 'png')
    assert datos == c['imagenes']['plan'][0]
    # Qué toca cada día, también en texto (los pausados no van)
    assert 'Lunes: Gym, Leer' in c['texto'] and 'Domingo: Leer, Llamar a la familia' in c['texto']
    assert 'Correr' not in c['texto'] and 'Correr' not in c['html']
    assert PlanEnviado.query.filter_by(idUser=user.idUser, anio=2026, mes=11).count() == 1


def test_sale_una_sola_vez_al_mes(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)
    correo.enviar_planes_mes(AHORA)
    correo.enviar_planes_mes(AHORA.replace(hour=9))
    correo.enviar_planes_mes(AHORA.replace(day=15))
    assert len(_planes(enviados)) == 1


def test_el_primer_dia_espera_a_la_hora(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_planes_mes(AHORA.replace(hour=correo.HORA_RESUMEN - 1)) == 0
    assert correo.enviar_planes_mes(AHORA.replace(hour=correo.HORA_RESUMEN)) == 1
    assert len(_planes(enviados)) == 1


def test_sin_plan_confirmado_espera_y_sale_al_confirmarlo(app, user, monkeypatch):
    _preparar(user, plan=False)
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_planes_mes(AHORA) == 0
    db.session.add(PlanMensual(idUser=user.idUser, anio=2026, mes=11))
    db.session.commit()
    assert correo.enviar_planes_mes(AHORA.replace(day=3)) == 1
    assert len(_planes(enviados)) == 1


def test_si_falla_se_reintenta_hasta_que_sale(app, user, monkeypatch):
    _preparar(user)
    app.config['MAIL_ENABLED'] = True

    def caido(*args, **kwargs):
        raise smtplib.SMTPException('caído')

    monkeypatch.setattr(correo, 'enviar_correo', caido)
    assert correo.enviar_planes_mes(AHORA) == 0
    assert PlanEnviado.query.count() == 0  # no quedó marcado como enviado

    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_planes_mes(AHORA.replace(hour=9)) == 1
    assert len(_planes(enviados)) == 1 and PlanEnviado.query.count() == 1


def test_sin_correo_configurado_no_se_marca(app, user):
    _preparar(user)
    app.config['MAIL_ENABLED'] = False
    assert correo.enviar_planes_mes(AHORA) == 0
    assert PlanEnviado.query.count() == 0


def test_sale_con_el_comando_de_recordatorios(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)
    correo.enviar_recordatorios(AHORA)
    assert len(_planes(enviados)) == 1


def test_solo_a_quien_pidio_correos_y_tiene_email(app, user, monkeypatch):
    _preparar(user, recordatorio=False)
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_planes_mes(AHORA) == 0
    user.email = None
    db.session.add(Recordatorio(idUser=user.idUser, hora='21:00'))
    db.session.commit()
    assert correo.enviar_planes_mes(AHORA) == 0
    assert _planes(enviados) == []


def test_sin_habitos_activos_no_sale(app, user, monkeypatch):
    user.email = 'persona@test.com'
    db.session.add(Recordatorio(idUser=user.idUser, hora='21:00'))
    db.session.add(PlanMensual(idUser=user.idUser, anio=2026, mes=11))
    db.session.commit()
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_planes_mes(AHORA) == 0 and _planes(enviados) == []


def test_el_correo_real_lleva_el_adjunto(app, user, monkeypatch):
    """Se arma el correo de verdad (sin mandarlo) y se revisa que lleve la imagen
    incrustada y el archivo adjunto."""
    _preparar(user)
    app.config.update(MAIL_ENABLED=True, MAIL_PORT=587, MAIL_SERVER='smtp.test', MAIL_USERNAME='u',
                      MAIL_PASSWORD='p', MAIL_FROM='app@test.com')
    capturados = []

    class SMTPFalso:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): pass
        def send_message(self, mensaje): capturados.append(mensaje.as_bytes())

    monkeypatch.setattr(correo.smtplib, 'SMTP', SMTPFalso)
    assert correo.enviar_planes_mes(AHORA) == 1
    mensaje = message_from_bytes(capturados[0])
    partes = list(mensaje.walk())
    adjuntos = [p for p in partes if p.get_filename() == 'plan-noviembre-2026.png']
    assert len(adjuntos) == 1 and adjuntos[0].get_content_type() == 'image/png'
    assert any(p.get('Content-ID') == '<plan>' for p in partes)
    assert Image.open(BytesIO(adjuntos[0].get_payload(decode=True))).format == 'PNG'


def test_borrar_cuenta_borra_los_envios(app, user):
    _preparar(user)
    db.session.add(PlanEnviado(idUser=user.idUser, anio=2026, mes=11))
    db.session.commit()
    id_user = user.idUser
    borrar_cuenta(user)
    db.session.commit()
    assert PlanEnviado.query.filter_by(idUser=id_user).count() == 0


# ── Personaje y colores ──

def _color_cabecera(png):
    """Color de la fila de los días (centro de la barra)."""
    return Image.open(BytesIO(png)).convert('RGB').getpixel((300, 308))


def test_cada_personaje_le_da_su_color():
    habitos = [('Leer', list(range(7)))]
    colores = {_color_cabecera(imagen_plan_png('Ana', habitos, 2026, 11, i)) for i in range(5)}
    assert len(colores) == 5


def test_la_imagen_lleva_al_personaje(app):
    habitos = [('Leer', list(range(7)))]
    with app.app_context():
        jpg = correo.imagen_personaje(0)
    sin = Image.open(BytesIO(imagen_plan_png('Ana', habitos, 2026, 11, 0))).convert('RGB')
    con = Image.open(BytesIO(imagen_plan_png('Ana', habitos, 2026, 11, 0, jpg))).convert('RGB')
    # Arriba a la derecha está el personaje; el resto de la imagen es igual
    zona = (800, 20, 1040, 250)
    assert sin.crop(zona).tobytes() != con.crop(zona).tobytes()
    assert sin.crop((0, 300, 1080, 400)).tobytes() == con.crop((0, 300, 1080, 400)).tobytes()


def test_el_correo_usa_el_mismo_personaje_en_la_imagen(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_plan_mes(user, HOY, personaje=2)
    (c,) = _planes(enviados)
    habitos = correo.habitos_del_plan(user.idUser)
    esperada = imagen_plan_png(user.nameUser, habitos, 2026, 11, 2, correo.imagen_personaje(2))
    assert c['imagenes']['plan'][0] == esperada
    assert c['imagenes']['personaje'][0] == correo.imagen_personaje(2)


# ── Las credenciales del correo no se filtran ──

CLAVE_SECRETA = 'clavesupersecreta123'


def _smtp_que_captura(capturados, falla_login=False):
    class SMTPFalso:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass

        def login(self, usuario, clave):
            if falla_login:
                raise smtplib.SMTPAuthenticationError(535, b'Username and Password not accepted')

        def send_message(self, mensaje): capturados.append(mensaje.as_bytes())
    return SMTPFalso


def test_la_clave_no_va_en_el_correo_ni_en_los_logs(app, user, monkeypatch, caplog):
    _preparar(user)
    app.config.update(MAIL_ENABLED=True, MAIL_PORT=587, MAIL_SERVER='smtp.test', MAIL_USERNAME='remitente@test.com',
                      MAIL_PASSWORD=CLAVE_SECRETA, MAIL_FROM='remitente@test.com')
    capturados = []
    monkeypatch.setattr(correo.smtplib, 'SMTP', _smtp_que_captura(capturados))
    assert correo.enviar_planes_mes(AHORA) == 1
    assert CLAVE_SECRETA.encode() not in capturados[0]

    # Si el servidor rechaza el login, el error queda en el log sin la clave
    db.session.query(PlanEnviado).delete()
    db.session.commit()
    monkeypatch.setattr(correo.smtplib, 'SMTP', _smtp_que_captura([], falla_login=True))
    with caplog.at_level('ERROR'):
        assert correo.enviar_planes_mes(AHORA) == 0
    assert 'No se pudo enviar el plan' in caplog.text
    assert CLAVE_SECRETA not in caplog.text


def test_la_imagen_y_el_texto_no_llevan_el_correo_del_usuario(app, user, monkeypatch):
    _preparar(user, email='privado.usuario@test.com')
    enviados = _capturar(monkeypatch, app)
    correo.enviar_planes_mes(AHORA)
    (c,) = _planes(enviados)
    assert 'privado.usuario' not in c['texto'] and 'privado.usuario' not in c['html']
    assert b'privado.usuario' not in c['imagenes']['plan'][0]
