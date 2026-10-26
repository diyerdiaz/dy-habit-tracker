"""Operaciones sobre la cuenta de un usuario que usan varias pantallas: borrarla
con todos sus datos (la propia persona o el administrador) y validar el cambio
de nombre de usuario o de contraseña (perfil normal y perfil del administrador)."""

from app import db
from app.models.users import User, mensaje_requisitos
from app.services.archivos import borrar_apuntes, borrar_foto, borrar_imagenes_vision

MAX_USUARIO = 80


def borrar_cuenta(user):
    """Borra la cuenta con todos sus datos y archivos (SQLite no aplica las FK en
    cascada). No hace commit: lo hace quien llama."""
    from app.models.codigos_recuperacion import CodigoRecuperacion
    from app.models.habitos import Habit
    from app.models.hist_habits import HistHabit
    from app.models.juego_partida import JuegoPartida
    from app.models.metodo_estudio import MetodoEstudio
    from app.models.plan_mensual import PlanMensual
    from app.models.recordatorios import Recordatorio, EnvioPrueba
    from app.models.recuperacion import Recuperacion, SesionRecuperacion
    from app.models.ruleta_castigo import Castigo
    from app.models.shadowing_sesion import ShadowingSesion
    from app.models.tareas import Tarea
    from app.models.temas import SesionExplicacion, TemaExplicar
    from app.models.user_progress import UserProgress
    from app.models.vision_board import MetaVision
    from app.models.vocabulario import Vocabulario
    from app.models.vocabulario_registro import VocabularioRegistro

    id_user = user.idUser
    borrar_foto(user)
    borrar_imagenes_vision(id_user, [m.imagen for m in MetaVision.query.filter_by(idUser=id_user).all()])
    for metodo in MetodoEstudio.query.filter_by(idUser=id_user).all():
        borrar_apuntes([a for t in metodo.tarjetas for a in t.apuntes])
        db.session.delete(metodo)  # en cascada: tarjetas del Kanban y apuntes
    # Primero lo que apunta a otras tablas del mismo usuario (sesiones -> temas, historial -> hábitos)
    for modelo in (SesionExplicacion, TemaExplicar, SesionRecuperacion, Recuperacion, HistHabit, Habit,
                   Castigo, Tarea, UserProgress, VocabularioRegistro, Vocabulario, ShadowingSesion,
                   Recordatorio, EnvioPrueba, CodigoRecuperacion, JuegoPartida, PlanMensual, MetaVision):
        modelo.query.filter_by(idUser=id_user).delete(synchronize_session=False)
    db.session.delete(user)


def error_cambio_usuario(user, nuevo, clave_actual):
    """(mensaje, categoría) si no se puede cambiar el nombre de usuario; None si sí."""
    if not nuevo or len(nuevo) > MAX_USUARIO:
        return f'Escribe un nombre de usuario (máximo {MAX_USUARIO} caracteres).', 'danger'
    if nuevo == user.nameUser:
        return 'Ese ya es tu nombre de usuario.', 'warning'
    if not user.check_password(clave_actual or ''):
        return 'La contraseña actual no es correcta.', 'danger'
    if User.query.filter(User.nameUser == nuevo, User.idUser != user.idUser).first():
        return 'Ese nombre de usuario ya está en uso. Elige otro.', 'danger'
    return None


def error_cambio_contrasena(user, clave_actual, nueva, confirmar):
    """(mensaje, categoría) si no se puede cambiar la contraseña; None si sí."""
    if not user.check_password(clave_actual or ''):
        return 'La contraseña actual no es correcta.', 'danger'
    if mensaje_requisitos(nueva):
        return mensaje_requisitos(nueva), 'danger'
    if nueva != confirmar:
        return 'La nueva contraseña y su confirmación no coinciden.', 'danger'
    if user.check_password(nueva):
        return 'La nueva contraseña debe ser distinta de la actual.', 'warning'
    return None
