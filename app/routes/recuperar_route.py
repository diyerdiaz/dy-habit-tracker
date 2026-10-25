"""Recuperar la contraseña con un código de 6 dígitos enviado al correo del perfil.

Paso 1 /recuperar/          usuario o correo -> se envía el código
Paso 2 /recuperar/codigo    se escribe el código (5 minutos, 3 intentos)
Paso 3 /recuperar/nueva     se crea la contraseña nueva
"""
import smtplib
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.models.users import User, mensaje_requisitos, MIN_LARGO_CONTRASENA
from app.models.intentos_login import IntentoLogin
from app.models.codigos_recuperacion import CodigoRecuperacion, MAX_INTENTOS, DIGITOS
from app.models.personajes_login import PERSONAJES
from app.services.correo import enviar_codigo, limite_codigo, avisar_contrasena_cambiada, ocultar_email

bp = Blueprint('recuperar', __name__, url_prefix='/recuperar')

SESION_USUARIO = 'recuperar_user'
SESION_CODIGO = 'recuperar_codigo'


def _render(plantilla, **datos):
    # Mismo personaje (y colores) que se estaba viendo en el login
    indice = session.get('personaje_login', 0)
    personaje = PERSONAJES[indice] if isinstance(indice, int) and 0 <= indice < len(PERSONAJES) else PERSONAJES[0]
    return render_template(plantilla, personaje=personaje, **datos)


def _buscar_usuario(identificador):
    """Busca por nombre de usuario o, si tiene @, por correo.
    Devuelve (usuario, mensaje de error)."""
    if '@' in identificador:
        usuarios = User.query.filter(func.lower(User.email) == identificador.lower()).all()
        if len(usuarios) > 1:
            return None, 'Ese correo está en varias cuentas. Escribe tu nombre de usuario.'
        usuario = usuarios[0] if usuarios else None
    else:
        usuario = User.query.filter_by(nameUser=identificador).first()
    if not usuario:
        return None, 'No encontramos ninguna cuenta con ese usuario o correo.'
    if not usuario.email:
        return None, ('Esa cuenta no tiene un correo registrado, así que no se puede recuperar por correo. '
                      'Si recuerdas tu contraseña, entra y agrega tu correo en Mi Perfil.')
    return usuario, None


def _enviar_nuevo_codigo(usuario):
    """Crea y envía un código. Devuelve True si se envió."""
    if not current_app.config.get('MAIL_ENABLED'):
        flash('El envío de correos no está disponible en este momento. Inténtalo más tarde.', 'danger')
        return False
    motivo = limite_codigo(usuario)
    if motivo:
        flash(motivo, 'warning')
        return False
    registro, codigo = CodigoRecuperacion.crear(usuario.idUser)
    try:
        enviar_codigo(usuario, codigo)
    except (smtplib.SMTPException, OSError):
        current_app.logger.exception('No se pudo enviar el código de recuperación')
        registro.anulado = True
        db.session.commit()
        flash('No se pudo enviar el correo. Inténtalo en unos minutos.', 'danger')
        return False
    session[SESION_USUARIO] = usuario.idUser
    session.pop(SESION_CODIGO, None)
    flash(f'Te enviamos un código de {DIGITOS} dígitos a {ocultar_email(usuario.email)}.', 'success')
    return True


def _usuario_en_proceso():
    idUser = session.get(SESION_USUARIO)
    return db.session.get(User, idUser) if idUser else None


@bp.route('/', methods=['GET', 'POST'])
def inicio():
    if current_user.is_authenticated:
        return redirect(url_for('perfil.index'))
    identificador = ''
    if request.method == 'POST':
        identificador = (request.form.get('identificador') or '').strip()
        if not identificador:
            flash('Escribe tu usuario o tu correo.', 'warning')
        else:
            usuario, error = _buscar_usuario(identificador)
            if error:
                flash(error, 'danger')
            elif _enviar_nuevo_codigo(usuario):
                return redirect(url_for('recuperar.codigo'))
    return _render('auth/recuperar.html', identificador=identificador)


@bp.route('/codigo', methods=['GET', 'POST'])
def codigo():
    usuario = _usuario_en_proceso()
    if not usuario:
        return redirect(url_for('recuperar.inicio'))
    registro = CodigoRecuperacion.activo(usuario.idUser)

    if request.method == 'POST':
        if not registro:
            flash('Ese código ya no sirve. Pide uno nuevo.', 'warning')
        else:
            resultado = registro.comprobar(request.form.get('codigo'))
            if resultado == 'ok':
                session[SESION_CODIGO] = registro.idCodigo
                return redirect(url_for('recuperar.nueva'))
            if resultado == 'vencido':
                flash('El código venció (dura 5 minutos). Pide uno nuevo.', 'warning')
            elif resultado == 'agotado':
                flash(f'Usaste los {MAX_INTENTOS} intentos. Ese código ya no sirve: pide uno nuevo.', 'danger')
            else:
                restantes = registro.intentos_restantes()
                flash(f"Código incorrecto. Te {'queda 1 intento' if restantes == 1 else f'quedan {restantes} intentos'}.", 'danger')
        registro = CodigoRecuperacion.activo(usuario.idUser)

    vigente = registro is not None and not registro.vencido()
    return _render(
        'auth/recuperar_codigo.html',
        email=ocultar_email(usuario.email),
        vigente=vigente,
        segundos=max(0, int((registro.expira - datetime.now()).total_seconds())) if vigente else 0,
        intentos=registro.intentos_restantes() if vigente else 0,
        digitos=DIGITOS,
    )


@bp.route('/reenviar', methods=['POST'])
def reenviar():
    usuario = _usuario_en_proceso()
    if not usuario:
        return redirect(url_for('recuperar.inicio'))
    _enviar_nuevo_codigo(usuario)
    return redirect(url_for('recuperar.codigo'))


@bp.route('/nueva', methods=['GET', 'POST'])
def nueva():
    usuario = _usuario_en_proceso()
    registro = db.session.get(CodigoRecuperacion, session.get(SESION_CODIGO) or 0)
    if not usuario or not registro or registro.idUser != usuario.idUser or not registro.puede_cambiar():
        session.pop(SESION_CODIGO, None)
        flash('Primero verifica el código que te enviamos.', 'warning')
        return redirect(url_for('recuperar.codigo' if usuario else 'recuperar.inicio'))

    if request.method == 'POST':
        nueva_clave = request.form.get('nueva_contrasena') or ''
        confirmar = request.form.get('confirmar_contrasena') or ''
        if mensaje_requisitos(nueva_clave):
            flash(mensaje_requisitos(nueva_clave), 'danger')
        elif nueva_clave != confirmar:
            flash('Las contraseñas no coinciden.', 'danger')
        else:
            usuario.set_password(nueva_clave)
            registro.anulado = True  # un código sirve una sola vez
            db.session.commit()
            # Quien recupera su contraseña puede entrar ya, aunque el login estuviera bloqueado
            IntentoLogin.limpiar(usuario.nameUser)
            session.pop(SESION_USUARIO, None)
            session.pop(SESION_CODIGO, None)
            avisar_contrasena_cambiada(usuario)
            flash('¡Listo! Tu contraseña se cambió. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
    return _render('auth/recuperar_nueva.html', usuario=usuario, min_password=MIN_LARGO_CONTRASENA)
