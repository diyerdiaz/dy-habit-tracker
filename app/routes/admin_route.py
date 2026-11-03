from datetime import date
from functools import wraps

from flask import Blueprint, render_template, abort, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from app import db
from app.models.habitos import Habit
from app.models.users import User
from app.services.admin import estadisticas_usuario, usuarios_registrados, resumen, habitos_del_dia, anotar_habito
from app.services.cuentas import borrar_cuenta, error_cambio_usuario, error_cambio_contrasena, MAX_USUARIO

bp = Blueprint('admin', __name__, url_prefix='/admin')


def solo_admin(vista):
    """Solo para administradores. A los demás les responde 404: ni saben que existe."""
    @wraps(vista)
    @login_required
    def envoltura(*args, **kwargs):
        if not current_user.es_admin:
            abort(404)
        return vista(*args, **kwargs)
    return envoltura


def _usuario_normal(id_user):
    """Usuario que el admin puede ver o gestionar (nunca otro administrador)."""
    user = db.session.get(User, id_user)
    if user is None or user.es_admin:
        abort(404)
    return user


@bp.route('/')
@solo_admin
def index():
    estadisticas = [estadisticas_usuario(u) for u in usuarios_registrados()]
    return render_template('admin/index.html', usuarios=estadisticas, resumen=resumen(estadisticas))


def _fecha_para_anotar(texto):
    """Fecha válida para anotar hábitos: hoy o un día pasado. None si no sirve."""
    try:
        fecha = date.fromisoformat(texto or '')
    except ValueError:
        return None
    return fecha if fecha <= date.today() else None


@bp.route('/usuarios/<int:id_user>')
@solo_admin
def detalle(id_user):
    user = _usuario_normal(id_user)
    fecha = _fecha_para_anotar(request.args.get('fecha')) or date.today()
    return render_template('admin/detalle.html', e=estadisticas_usuario(user),
                           fecha=fecha, hoy=date.today(), habitos=habitos_del_dia(user, fecha))


@bp.route('/usuarios/<int:id_user>/habitos/<int:id_habit>/anotar', methods=['POST'])
@solo_admin
def anotar(id_user, id_habit):
    """El admin marca o desmarca un hábito del usuario en un día (por si él no pudo)."""
    user = _usuario_normal(id_user)
    habito = Habit.visibles(user.idUser).filter_by(idHabit=id_habit).first_or_404()
    fecha = _fecha_para_anotar(request.form.get('fecha'))
    if fecha is None:
        flash('Elige una fecha válida: hoy o un día pasado.', 'danger')
        return redirect(url_for('admin.detalle', id_user=user.idUser, _anchor='anotar'))
    marcado = anotar_habito(user, habito, fecha)
    dia = fecha.strftime('%d/%m/%Y')
    if marcado:
        flash(f'"{habito.habitName}" quedó anotado para {user.nameUser} el {dia}.', 'success')
    else:
        flash(f'Se quitó "{habito.habitName}" de {user.nameUser} el {dia}.', 'info')
    return redirect(url_for('admin.detalle', id_user=user.idUser, fecha=fecha.isoformat(), _anchor='anotar'))


@bp.route('/usuarios/<int:id_user>/bloquear', methods=['POST'])
@solo_admin
def bloquear(id_user):
    """Bloquea o desbloquea. El bloqueado no puede entrar y su sesión abierta se cierra sola."""
    user = _usuario_normal(id_user)
    user.bloqueado = not user.bloqueado
    db.session.commit()
    if user.bloqueado:
        flash(f'"{user.nameUser}" quedó bloqueado: ya no puede iniciar sesión.', 'warning')
    else:
        flash(f'"{user.nameUser}" fue desbloqueado: ya puede volver a entrar.', 'success')
    return redirect(url_for('admin.detalle', id_user=user.idUser))


@bp.route('/usuarios/<int:id_user>/eliminar', methods=['POST'])
@solo_admin
def eliminar(id_user):
    user = _usuario_normal(id_user)
    # Se escribe el nombre para confirmar: evita borrar a alguien por un clic equivocado
    if (request.form.get('confirmar') or '').strip() != user.nameUser:
        flash('Para eliminar la cuenta escribe exactamente su nombre de usuario.', 'danger')
        return redirect(url_for('admin.detalle', id_user=user.idUser))
    nombre = user.nameUser
    borrar_cuenta(user)
    db.session.commit()
    flash(f'La cuenta "{nombre}" y todos sus datos fueron eliminados.', 'info')
    return redirect(url_for('admin.index'))


@bp.route('/perfil')
@solo_admin
def perfil():
    return render_template('admin/perfil.html', max_usuario=MAX_USUARIO)


@bp.route('/perfil/usuario', methods=['POST'])
@solo_admin
def cambiar_usuario():
    nuevo = (request.form.get('nuevo_usuario') or '').strip()
    error = error_cambio_usuario(current_user, nuevo, request.form.get('contrasena_actual'))
    if error:
        flash(*error)
    else:
        current_user.nameUser = nuevo
        db.session.commit()
        flash(f'Listo, ahora tu usuario es "{nuevo}".', 'success')
    return redirect(url_for('admin.perfil'))


@bp.route('/perfil/contrasena', methods=['POST'])
@solo_admin
def cambiar_contrasena():
    nueva = request.form.get('nueva_contrasena') or ''
    error = error_cambio_contrasena(current_user, request.form.get('contrasena_actual'),
                                    nueva, request.form.get('confirmar_contrasena') or '')
    if error:
        flash(*error)
    else:
        current_user.cambiar_contrasena(nueva)
        db.session.commit()
        # Esta sesión sigue abierta; las de otros equipos se cierran
        session['sesion_version'] = current_user.sesionVersion
        flash('Tu contraseña se cambió correctamente.', 'success')
    return redirect(url_for('admin.perfil'))
