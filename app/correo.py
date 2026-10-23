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
from app.gamificacion import calcular_racha
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.personajes_login import PERSONAJES, elegir_personaje
from app.models.recordatorios import Recordatorio
from app.models.users import User

logger = logging.getLogger(__name__)

# Si el comando se ejecuta más tarde que la hora del recordatorio (equipo apagado,
# cron atrasado), aún se envía dentro de esta ventana; después se salta ese día.
VENTANA_MINUTOS = 60


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
