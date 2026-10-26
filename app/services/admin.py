"""Panel de administración: estadísticas de los usuarios registrados y el comando
`flask --app run crear-admin` para crear la cuenta de administrador."""

from datetime import date, timedelta

import click
from sqlalchemy import func

import logging

from flask import current_app

from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.shadowing_sesion import ShadowingSesion
from app.models.tareas import Tarea
from app.models.user_progress import UserProgress
from app.models.users import User, ROL_ADMIN, mensaje_requisitos
from app.models.vision_board import MetaVision
from app.models.vocabulario import Vocabulario
from app.services.correo import ocultar_email
from app.services.gamificacion import calcular_racha
from app.services.level_config import calcular_progreso

# Días que se muestran en la tira de actividad del detalle de un usuario
DIAS_ACTIVIDAD = 30

logger = logging.getLogger(__name__)


def _contar(modelo, idUser, *filtros):
    return db.session.query(func.count()).select_from(modelo).filter(modelo.idUser == idUser, *filtros).scalar()


def estadisticas_usuario(user, hoy=None):
    """Números de un usuario para el panel. Solo conteos: nada de lo que escribió."""
    hoy = hoy or date.today()
    desde = hoy - timedelta(days=DIAS_ACTIVIDAD - 1)
    dias_activos = {f for (f,) in db.session.query(HistHabit.fecha).filter(
        HistHabit.idUser == user.idUser, HistHabit.fecha >= desde, HistHabit.fecha <= hoy).distinct()}
    ultima = db.session.query(func.max(HistHabit.fecha)).filter(HistHabit.idUser == user.idUser).scalar()
    progreso = db.session.get(UserProgress, user.idUser)
    xp = progreso.xpTotal if progreso else 0
    habitos = _contar(Habit, user.idUser)
    racha, racha_maxima = calcular_racha(user.idUser)
    segundos = db.session.query(func.coalesce(func.sum(ShadowingSesion.duracionSegundos), 0)).filter(
        ShadowingSesion.idUser == user.idUser).scalar()
    return {
        'id': user.idUser,
        'usuario': user.nameUser,
        'correo': ocultar_email(user.email) if user.email else None,
        'bloqueado': user.bloqueado,
        'nivel': calcular_progreso(xp, habitos)['nivel'],
        'xp': xp,
        'racha': racha,
        'racha_maxima': racha_maxima,
        'habitos': habitos,
        'habitos_activos': _contar(Habit, user.idUser, Habit.habitState == 'Activo'),
        'marcados': _contar(HistHabit, user.idUser),
        'dias_activos_30': len(dias_activos),
        'actividad': [(desde + timedelta(days=i), (desde + timedelta(days=i)) in dias_activos)
                      for i in range(DIAS_ACTIVIDAD)],
        'ultima_actividad': ultima,
        'dias_sin_actividad': (hoy - ultima).days if ultima else None,
        'tareas': _contar(Tarea, user.idUser),
        'tareas_hechas': _contar(Tarea, user.idUser, Tarea.completada.is_(True)),
        'metas': _contar(MetaVision, user.idUser),
        'metas_logradas': _contar(MetaVision, user.idUser, MetaVision.cumplida.is_(True)),
        'palabras': _contar(Vocabulario, user.idUser),
        'minutos_shadowing': round((segundos or 0) / 60),
    }


def usuarios_registrados():
    """Usuarios normales (los administradores no aparecen en la lista)."""
    return User.query.filter(User.rol != ROL_ADMIN).order_by(User.nameUser).all()


def resumen(estadisticas, hoy=None):
    """Totales de arriba del panel a partir de las estadísticas de cada usuario."""
    hoy = hoy or date.today()
    activos = lambda dias: sum(1 for e in estadisticas
                               if e['ultima_actividad'] and (hoy - e['ultima_actividad']).days < dias)
    return {
        'usuarios': len(estadisticas),
        'activos_hoy': activos(1),
        'activos_7': activos(7),
        'con_correo': sum(1 for e in estadisticas if e['correo']),
        'marcados': sum(e['marcados'] for e in estadisticas),
    }


def crear_admin(nombre, clave):
    """Crea la cuenta de administrador. Devuelve (user, None) o (None, mensaje de error)."""
    nombre = (nombre or '').strip()
    if not nombre or len(nombre) > 80:
        return None, 'Escribe un nombre de usuario válido (máx. 80 caracteres).'
    if User.query.filter_by(nameUser=nombre).first():
        return None, f"El usuario '{nombre}' ya existe. Elige otro nombre para el administrador."
    error = mensaje_requisitos(clave)
    if error:
        return None, error
    admin = User(nameUser=nombre, password=clave, rol=ROL_ADMIN)
    db.session.add(admin)
    db.session.commit()
    return admin, None


def asegurar_admin_del_entorno():
    """Al arrancar: crea el administrador con ADMIN_USUARIO / ADMIN_CONTRASENA si
    todavía no existe. Si ya existe no lo toca (su contraseña pudo cambiarse en
    "Mi perfil"). Nunca convierte en admin a un usuario normal. Devuelve qué pasó."""
    nombre = (current_app.config.get('ADMIN_USUARIO') or '').strip()
    clave = current_app.config.get('ADMIN_CONTRASENA') or ''
    if not nombre or not clave:
        return 'sin_configurar'
    existente = User.query.filter_by(nameUser=nombre).first()
    if existente and existente.es_admin:
        return 'ya_existe'
    if existente:
        logger.warning("ADMIN_USUARIO '%s' ya es una cuenta de usuario normal: no se convierte en admin. "
                       "Usa otro nombre en ADMIN_USUARIO.", nombre)
        return 'nombre_ocupado'
    _, error = crear_admin(nombre, clave)
    if error:
        # Solo el motivo: la contraseña nunca va al log
        logger.error("No se creó el administrador '%s' de ADMIN_USUARIO: %s", nombre, error)
        return 'error'
    logger.info("Administrador '%s' creado desde las variables de entorno.", nombre)
    return 'creado'


def registrar_comandos(app):
    @app.cli.command('crear-admin')
    @click.argument('nombre')
    def crear_admin_cmd(nombre):
        """Crea una cuenta de administrador (pide la contraseña sin mostrarla)."""
        clave = click.prompt('Contraseña', hide_input=True, confirmation_prompt='Repite la contraseña')
        admin, error = crear_admin(nombre, clave)
        if error:
            raise click.ClickException(error)
        click.echo(f"Administrador '{admin.nameUser}' creado. Entra con él en el login: verás solo el panel /admin.")

