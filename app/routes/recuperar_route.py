"""Recuperar la contraseña con un código de 6 dígitos enviado al correo del perfil.

Paso 1 /recuperar/          usuario o correo -> se envía el código
Paso 2 /recuperar/codigo    se escribe el código (5 minutos, 3 intentos)
Paso 3 /recuperar/nueva     se crea la contraseña nueva
"""
import smtplib
import threading
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.models.users import User, mensaje_requisitos, MIN_LARGO_CONTRASENA
from app.models.intentos_login import IntentoLogin
from app.models.codigos_recuperacion import CodigoRecuperacion, MAX_INTENTOS, DIGITOS, MINUTOS_VALIDEZ
from app.services.personajes_login import PERSONAJES
from app.services.correo import enviar_codigo, limite_codigo, avisar_contrasena_cambiada

bp = Blueprint('recuperar', __name__, url_prefix='/recuperar')

SESION_USUARIO = 'recuperar_user'
SESION_CODIGO = 'recuperar_codigo'


def _render(plantilla, **datos):
    # Mismo personaje (y colores) que se estaba viendo en el login
    indice = session.get('personaje_login', 0)
    personaje = PERSONAJES[indice] if isinstance(indice, int) and 0 <= indice < len(PERSONAJES) else PERSONAJES[0]
    return render_template(plantilla, personaje=personaje, **datos)


# La respuesta es la misma exista o no la cuenta, tenga o no correo, o si ya pidió
# demasiados códigos: así nadie puede averiguar qué usuarios o correos existen.
MENSAJE_ENVIADO = ('Si el usuario o correo corresponde a una cuenta con correo registrado, te enviamos '
                   f'un código de {DIGITOS} dígitos. Revisa también la carpeta de spam. '
                   'Si no te llega, espera un minuto y pide otro.')
# Cuándo se pidió el código y cuántos se escribieron mal, para que la pantalla del
# código se comporte igual aunque no se haya enviado ninguno de verdad
SESION_PEDIDO = 'recuperar_pedido'
SESION_FALLOS = 'recuperar_fallos'


def _buscar_usuario(identificador):
    """Cuenta a la que se le puede enviar el código, o None (sin decir por qué)."""
    if '@' in identificador:
        usuarios = User.query.filter(func.lower(User.email) == identificador.lower()).all()
        # Un correo en varias cuentas no dice cuál es: hay que usar el nombre de usuario
        usuario = usuarios[0] if len(usuarios) == 1 else None
    else:
        usuario = User.query.filter_by(nameUser=identificador).first()
    return usuario if usuario and usuario.email else None


def _enviar(idUser, idCodigo, codigo):
    usuario = db.session.get(User, idUser)
    try:
        enviar_codigo(usuario, codigo)
    except (smtplib.SMTPException, OSError):
        current_app.logger.exception('No se pudo enviar el código de recuperación')
        registro = db.session.get(CodigoRecuperacion, idCodigo)
        registro.anulado = True
        db.session.commit()


def _enviar_en_segundo_plano(app, idUser, idCodigo, codigo):
    with app.app_context():
        _enviar(idUser, idCodigo, codigo)


def _enviar_nuevo_codigo(usuario):
    """Crea y envía un código si se puede. No avisa si no se pudo: la pantalla
    tiene que verse igual para una cuenta que existe y para una que no."""
    if usuario is None or limite_codigo(usuario):
        return
    registro, codigo = CodigoRecuperacion.crear(usuario.idUser)
    app = current_app._get_current_object()
    if app.testing:
        _enviar(usuario.idUser, registro.idCodigo, codigo)  # en los tests, sin hilos
    else:
        # El correo tarda segundos: si se esperara aquí, el tiempo de respuesta
        # delataría que la cuenta existe
        threading.Thread(target=_enviar_en_segundo_plano,
                         args=(app, usuario.idUser, registro.idCodigo, codigo), daemon=True).start()


def _empezar(usuario):
    session[SESION_USUARIO] = usuario.idUser if usuario else None
    session[SESION_PEDIDO] = datetime.now().isoformat()
    session[SESION_FALLOS] = 0
    session.pop(SESION_CODIGO, None)


def _en_proceso():
    return SESION_PEDIDO in session


def _usuario_en_proceso():
    idUser = session.get(SESION_USUARIO)
    return db.session.get(User, idUser) if idUser else None


def _correo_disponible():
    if current_app.config.get('MAIL_ENABLED'):
        return True
    # Es del servidor, no de la cuenta: decirlo no revela nada
    flash('El envío de correos no está disponible en este momento. Inténtalo más tarde.', 'danger')
    return False


@bp.route('/', methods=['GET', 'POST'])
def inicio():
    if current_user.is_authenticated:
        return redirect(url_for('perfil.index'))
    identificador = ''
    if request.method == 'POST':
        identificador = (request.form.get('identificador') or '').strip()
        if not identificador:
            flash('Escribe tu usuario o tu correo.', 'warning')
        elif _correo_disponible():
            usuario = _buscar_usuario(identificador)
            _enviar_nuevo_codigo(usuario)
            _empezar(usuario)
            flash(MENSAJE_ENVIADO, 'info')
            return redirect(url_for('recuperar.codigo'))
    return _render('auth/recuperar.html', identificador=identificador)


def _estado_simulado():
    """Tiempo e intentos que se muestran cuando no hay un código real activo
    (cuenta inexistente, sin correo o con el límite de códigos alcanzado)."""
    try:
        pedido = datetime.fromisoformat(session.get(SESION_PEDIDO))
    except (TypeError, ValueError):
        pedido = datetime.now()
    expira = pedido + timedelta(minutes=MINUTOS_VALIDEZ)
    fallos = session.get(SESION_FALLOS, 0)
    return expira, max(0, MAX_INTENTOS - fallos)


@bp.route('/codigo', methods=['GET', 'POST'])
def codigo():
    if not _en_proceso():
        return redirect(url_for('recuperar.inicio'))
    usuario = _usuario_en_proceso()
    registro = CodigoRecuperacion.activo(usuario.idUser) if usuario else None

    if request.method == 'POST':
        if registro:
            resultado = registro.comprobar(request.form.get('codigo'))
            restantes = registro.intentos_restantes()
            # Si el código real se anula, la pantalla sigue igual que una simulada
            session[SESION_FALLOS] = MAX_INTENTOS - restantes
        else:
            # Sin código real: se responde igual que con uno que no coincide
            expira, restantes = _estado_simulado()
            if datetime.now() >= expira:
                resultado = 'vencido'
            elif restantes <= 0:
                resultado = 'sin_codigo'
            else:
                session[SESION_FALLOS] = session.get(SESION_FALLOS, 0) + 1
                restantes -= 1
                resultado = 'agotado' if restantes == 0 else 'incorrecto'
        if resultado == 'ok':
            session[SESION_CODIGO] = registro.idCodigo
            return redirect(url_for('recuperar.nueva'))
        if resultado == 'vencido':
            flash('El código venció (dura 5 minutos). Pide uno nuevo.', 'warning')
        elif resultado == 'agotado':
            flash(f'Usaste los {MAX_INTENTOS} intentos. Ese código ya no sirve: pide uno nuevo.', 'danger')
        elif resultado == 'sin_codigo':
            flash('Ese código ya no sirve. Pide uno nuevo.', 'warning')
        else:
            flash(f"Código incorrecto. Te {'queda 1 intento' if restantes == 1 else f'quedan {restantes} intentos'}.", 'danger')
        registro = CodigoRecuperacion.activo(usuario.idUser) if usuario else None

    if registro and not registro.vencido():
        vigente, segundos, intentos = True, (registro.expira - datetime.now()).total_seconds(), registro.intentos_restantes()
    else:
        expira, intentos = _estado_simulado()
        segundos = (expira - datetime.now()).total_seconds()
        vigente = segundos > 0 and intentos > 0
    return _render(
        'auth/recuperar_codigo.html',
        vigente=vigente,
        segundos=max(0, int(segundos)) if vigente else 0,
        intentos=intentos if vigente else 0,
        digitos=DIGITOS,
    )


@bp.route('/reenviar', methods=['POST'])
def reenviar():
    if not _en_proceso():
        return redirect(url_for('recuperar.inicio'))
    if _correo_disponible():
        usuario = _usuario_en_proceso()
        _enviar_nuevo_codigo(usuario)
        _empezar(usuario)
        flash(MENSAJE_ENVIADO, 'info')
    return redirect(url_for('recuperar.codigo'))


@bp.route('/nueva', methods=['GET', 'POST'])
def nueva():
    usuario = _usuario_en_proceso()
    registro = db.session.get(CodigoRecuperacion, session.get(SESION_CODIGO) or 0)
    if not usuario or not registro or registro.idUser != usuario.idUser or not registro.puede_cambiar():
        session.pop(SESION_CODIGO, None)
        flash('Primero verifica el código que te enviamos.', 'warning')
        return redirect(url_for('recuperar.codigo' if _en_proceso() else 'recuperar.inicio'))

    if request.method == 'POST':
        nueva_clave = request.form.get('nueva_contrasena') or ''
        confirmar = request.form.get('confirmar_contrasena') or ''
        if mensaje_requisitos(nueva_clave):
            flash(mensaje_requisitos(nueva_clave), 'danger')
        elif nueva_clave != confirmar:
            flash('Las contraseñas no coinciden.', 'danger')
        else:
            usuario.cambiar_contrasena(nueva_clave)  # cierra todas sus sesiones abiertas
            registro.anulado = True  # un código sirve una sola vez
            db.session.commit()
            # Quien recupera su contraseña puede entrar ya, aunque el login estuviera bloqueado
            IntentoLogin.limpiar_usuario(usuario.nameUser)
            for clave in (SESION_USUARIO, SESION_CODIGO, SESION_PEDIDO, SESION_FALLOS):
                session.pop(clave, None)
            avisar_contrasena_cambiada(usuario)
            flash('¡Listo! Tu contraseña se cambió. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
    return _render('auth/recuperar_nueva.html', usuario=usuario, min_password=MIN_LARGO_CONTRASENA)
