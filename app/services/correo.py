"""Envío de correos (SMTP) con los hábitos pendientes del día.

El comando `flask --app run enviar-recordatorios` revisa los recordatorios cuya
hora ya llegó y envía el correo. Hay que ejecutarlo periódicamente (cron cada
5-10 minutos, o una tarea programada en Coolify)."""

import logging
import os
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage

import click
from flask import current_app

from app import db
from app.services.gamificacion import calcular_racha
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.services.personajes_login import PERSONAJES, elegir_personaje
from app.models.recordatorios import Recordatorio, EnvioPrueba
from app.models.codigos_recuperacion import CodigoRecuperacion, MINUTOS_VALIDEZ
from app.models.users import User

logger = logging.getLogger(__name__)

# Si el comando se ejecuta más tarde que la hora del recordatorio (equipo apagado,
# cron atrasado), aún se envía dentro de esta ventana; después se salta ese día.
VENTANA_MINUTOS = 60

# Límites del botón "Enviarme un correo de prueba" del perfil
PRUEBA_ESPERA_SEGUNDOS = 60      # entre dos pruebas del mismo usuario
PRUEBA_MAX_DIA_USUARIO = 5
PRUEBA_MAX_DIA_DESTINO = 5       # a una misma dirección, aunque sean varias cuentas
PRUEBA_MAX_DIA_TOTAL = 100       # toda la app (Gmail permite ~500 al día)

# Límites de los códigos para recuperar la contraseña
CODIGO_ESPERA_SEGUNDOS = 60
CODIGO_MAX_DIA_USUARIO = 5
CODIGO_MAX_DIA_TOTAL = 100


def habitos_pendientes(idUser, fecha=None):
    """Hábitos activos que tocan ese día y que todavía no se marcaron."""
    fecha = fecha or date.today()
    hechos = {h.idHabit for h in HistHabit.query.filter_by(idUser=idUser, fecha=fecha).all()}
    habitos = Habit.query.filter_by(idUser=idUser, habitState='Activo').order_by(Habit.habitName).all()
    return [h for h in habitos if h.toca_el(fecha) and h.idHabit not in hechos]


def enviar_correo(destino, asunto, texto, html=None, imagenes=None):
    """Envía un correo. Devuelve False si el correo no está configurado.
    `imagenes`: {cid: (bytes, subtipo)} que el HTML usa como src="cid:<cid>".
    Si el servidor SMTP falla, lanza la excepción (smtplib.SMTPException / OSError)."""
    cfg = current_app.config
    if not cfg.get('MAIL_ENABLED'):
        return False
    mensaje = EmailMessage()
    mensaje['Subject'] = asunto
    mensaje['From'] = cfg['MAIL_FROM']
    mensaje['To'] = destino
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype='html')
        parte_html = mensaje.get_payload()[1]
        for cid, (datos, subtipo) in (imagenes or {}).items():
            # Imagen incrustada en el correo: se ve aunque la app no esté publicada
            parte_html.add_related(datos, maintype='image', subtype=subtipo, cid=f'<{cid}>')

    if cfg['MAIL_PORT'] == 465:
        servidor = smtplib.SMTP_SSL(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=20)
    else:
        servidor = smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=20)
    with servidor:
        if cfg['MAIL_PORT'] != 465:
            servidor.starttls()
        servidor.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
        servidor.send_message(mensaje)
    return True


def imagen_personaje(indice):
    """JPG liviano del personaje del login para incrustar en el correo
    (Gmail no muestra SVG). Se generan desde los SVG de static/img/personajes/."""
    ruta = os.path.join(current_app.static_folder, 'img', 'personajes', f'correo-personaje-{indice + 1}.jpg')
    with open(ruta, 'rb') as f:
        return f.read()


def datos_correo(user, fecha, prueba=False, personaje=None):
    """Todo lo que necesitan las plantillas del correo de recordatorio."""
    pendientes = habitos_pendientes(user.idUser, fecha)
    racha, _ = calcular_racha(user.idUser)
    marcado_hoy = HistHabit.query.filter_by(idUser=user.idUser, fecha=fecha).first() is not None
    if personaje is None:
        personaje = elegir_personaje()
    app_url = (current_app.config.get('APP_URL') or '').rstrip('/')
    return dict(
        user=user, pendientes=pendientes, fecha=fecha, prueba=prueba,
        racha=racha, racha_en_riesgo=racha > 0 and not marcado_hoy,
        personaje=PERSONAJES[personaje], indice_personaje=personaje,
        tema=PERSONAJES[personaje]['tema'],
        url_check=f'{app_url}/habitos/check' if app_url else None,
        url_perfil=f'{app_url}/perfil/#recordatorios' if app_url else None,
    )


def enviar_pendientes(user, fecha=None, prueba=False, personaje=None):
    """Envía a `user` el correo con sus pendientes del día.
    Sin pendientes no envía nada, salvo que sea una prueba desde el perfil.
    Devuelve True si se envió."""
    if not user.email:
        return False
    fecha = fecha or date.today()
    datos = datos_correo(user, fecha, prueba, personaje)
    pendientes = datos['pendientes']
    if not pendientes and not prueba:
        return False
    if pendientes:
        n = len(pendientes)
        asunto = f"Te {'falta 1 hábito' if n == 1 else f'faltan {n} hábitos'} hoy"
        if datos['racha_en_riesgo']:
            asunto += f" · no pierdas tu racha de {datos['racha']} {'día' if datos['racha'] == 1 else 'días'}"
    else:
        asunto = "¡Vas al día con tus hábitos!"
    if prueba:
        asunto = f"Prueba: {asunto}"
    return enviar_correo(
        user.email,
        asunto,
        _render('correos/recordatorio.txt', **datos),
        _render('correos/recordatorio.html', **datos),
        imagenes={'personaje': (imagen_personaje(datos['indice_personaje']), 'jpeg')},
    )


def _render(plantilla, **datos):
    # Sin render_template: el comando programado no tiene petición HTTP (ni sesión)
    # y los context processors de la app la necesitan
    return current_app.jinja_env.get_template(plantilla).render(**datos)


def limite_prueba(user, ahora=None):
    """Mensaje de por qué no se puede enviar otra prueba ahora, o None si se puede."""
    ahora = ahora or datetime.now()
    inicio_dia = datetime.combine(ahora.date(), datetime.min.time())
    hoy = EnvioPrueba.query.filter(EnvioPrueba.createdAt >= inicio_dia)
    ultima = (EnvioPrueba.query.filter_by(idUser=user.idUser)
              .order_by(EnvioPrueba.createdAt.desc()).first())
    if ultima and (ahora - ultima.createdAt).total_seconds() < PRUEBA_ESPERA_SEGUNDOS:
        return 'Espera un minuto antes de pedir otro correo de prueba.'
    if hoy.filter_by(idUser=user.idUser).count() >= PRUEBA_MAX_DIA_USUARIO:
        return f'Ya enviaste {PRUEBA_MAX_DIA_USUARIO} correos de prueba hoy. Inténtalo mañana.'
    if hoy.filter_by(email=user.email).count() >= PRUEBA_MAX_DIA_DESTINO:
        return 'Esa dirección ya recibió muchos correos de prueba hoy. Inténtalo mañana.'
    if hoy.count() >= PRUEBA_MAX_DIA_TOTAL:
        return 'Se alcanzó el límite de correos de prueba de hoy. Inténtalo mañana.'
    return None


def registrar_prueba(user, ahora=None):
    """Cuenta el intento (aunque luego falle el SMTP) y limpia registros viejos."""
    ahora = ahora or datetime.now()
    EnvioPrueba.query.filter(EnvioPrueba.createdAt < ahora - timedelta(days=2)).delete(synchronize_session=False)
    db.session.add(EnvioPrueba(idUser=user.idUser, email=user.email, createdAt=ahora))
    db.session.commit()


def limite_codigo(user, ahora=None):
    """Mensaje de por qué no se puede enviar otro código ahora, o None si se puede."""
    ahora = ahora or datetime.now()
    inicio_dia = datetime.combine(ahora.date(), datetime.min.time())
    hoy = CodigoRecuperacion.query.filter(CodigoRecuperacion.createdAt >= inicio_dia)
    ultimo = (CodigoRecuperacion.query.filter_by(idUser=user.idUser)
              .order_by(CodigoRecuperacion.createdAt.desc()).first())
    if ultimo and (ahora - ultimo.createdAt).total_seconds() < CODIGO_ESPERA_SEGUNDOS:
        return 'Espera un minuto antes de pedir otro código.'
    if hoy.filter_by(idUser=user.idUser).count() >= CODIGO_MAX_DIA_USUARIO:
        return f'Ya pediste {CODIGO_MAX_DIA_USUARIO} códigos hoy. Inténtalo mañana.'
    if hoy.count() >= CODIGO_MAX_DIA_TOTAL:
        return 'No podemos enviar más códigos hoy. Inténtalo mañana.'
    return None


def enviar_codigo(user, codigo, personaje=None):
    """Envía el código de recuperación con el diseño de la app (personaje incrustado)."""
    if personaje is None:
        personaje = elegir_personaje()
    datos = dict(user=user, codigo=codigo, minutos=MINUTOS_VALIDEZ,
                 personaje=PERSONAJES[personaje], tema=PERSONAJES[personaje]['tema'])
    return enviar_correo(
        user.email,
        f'Tu código para recuperar la contraseña: {codigo}',
        _render('correos/codigo.txt', **datos),
        _render('correos/codigo.html', **datos),
        imagenes={'personaje': (imagen_personaje(personaje), 'jpeg')},
    )


def avisar_contrasena_cambiada(user, personaje=None):
    """Aviso de seguridad tras cambiar la contraseña con un código. Si falla, solo se registra."""
    if personaje is None:
        personaje = elegir_personaje()
    app_url = (current_app.config.get('APP_URL') or '').rstrip('/')
    datos = dict(user=user, ahora=datetime.now(), personaje=PERSONAJES[personaje],
                 tema=PERSONAJES[personaje]['tema'],
                 url_recuperar=f'{app_url}/recuperar/' if app_url else None)
    try:
        enviar_correo(
            user.email, 'Tu contraseña se cambió',
            _render('correos/contrasena_cambiada.txt', **datos),
            _render('correos/contrasena_cambiada.html', **datos),
            imagenes={'personaje': (imagen_personaje(personaje), 'jpeg')},
        )
    except (smtplib.SMTPException, OSError):
        logger.exception('No se pudo enviar el aviso de contraseña cambiada a %s', user.idUser)


def ocultar_email(email):
    """d***z7@gmail.com: para mostrar a dónde se envió el código sin revelar el correo completo."""
    usuario, _, dominio = (email or '').partition('@')
    if len(usuario) <= 2:
        visible = usuario[:1] + '***'
    else:
        visible = usuario[0] + '***' + usuario[-2:]
    return f'{visible}@{dominio}'


def toca_enviar(recordatorio, ahora):
    """True si la hora del recordatorio ya llegó (dentro de la ventana) y hoy no se ha enviado."""
    if recordatorio.ultimoEnvio == ahora.date():
        return False
    programado = datetime.combine(ahora.date(), recordatorio.hora_time())
    return programado <= ahora < programado + timedelta(minutes=VENTANA_MINUTOS)


def enviar_recordatorios(ahora=None):
    """Revisa todos los recordatorios y envía los que tocan. Devuelve cuántos correos salieron."""
    ahora = ahora or datetime.now()
    enviados = 0
    recordatorios = (Recordatorio.query.join(User, User.idUser == Recordatorio.idUser)
                     .filter(User.email.isnot(None), User.email != '').all())
    for rec in recordatorios:
        if not toca_enviar(rec, ahora):
            continue
        user = db.session.get(User, rec.idUser)
        try:
            if enviar_pendientes(user, ahora.date()):
                enviados += 1
        except (smtplib.SMTPException, OSError):
            # No se marca como enviado: se reintenta en la próxima ejecución
            logger.exception("No se pudo enviar el recordatorio %s", rec.idRecordatorio)
            continue
        rec.ultimoEnvio = ahora.date()
        db.session.commit()
    return enviados


def registrar_comandos(app):
    @app.cli.command('enviar-recordatorios')
    def enviar_recordatorios_cmd():
        """Envía los correos de hábitos pendientes cuya hora ya llegó."""
        if not app.config.get('MAIL_ENABLED'):
            click.echo('El correo no está configurado (MAIL_USERNAME / MAIL_PASSWORD en .env).')
            return
        click.echo(f'Correos enviados: {enviar_recordatorios()}')
