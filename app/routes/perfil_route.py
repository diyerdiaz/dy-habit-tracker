import os
import uuid
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, send_from_directory, abort,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from flask_login import login_required, current_user
from app import db
from app.models.users import User
from app.models.habitos import Habit
from app.models.medallas import obtener_metricas, evaluar_medallas
from app.gamificacion import get_or_create_progress
from app.level_config import calcular_progreso

bp = Blueprint('perfil', __name__, url_prefix='/perfil')

MIN_PASSWORD = 6
MAX_USUARIO = 80
TAMANO_FOTO = 400          # la foto se guarda recortada en un cuadrado de 400x400
MAX_FOTO_MB = 8
EXTENSIONES_FOTO = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def carpeta_avatars():
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')


def borrar_foto(user):
    if user.avatar:
        try:
            os.remove(os.path.join(carpeta_avatars(), user.avatar))
        except FileNotFoundError:
            pass
        user.avatar = None


def _contrasena_actual_ok():
    """Todo cambio de cuenta exige la contraseña actual."""
    if current_user.check_password(request.form.get('contrasena_actual') or ''):
        return True
    flash('La contraseña actual no es correcta.', 'danger')
    return False


@bp.route('/')
@login_required
def index():
    progress = get_or_create_progress(current_user.idUser)
    habitos = Habit.query.filter_by(idUser=current_user.idUser).count()
    progreso = calcular_progreso(progress.xpTotal, habitos)
    medallas = evaluar_medallas(obtener_metricas(current_user.idUser))
    return render_template(
        'perfil/index.html',
        progreso=progreso,
        xp=progress.xpTotal,
        racha=progress.rachaActual,
        habitos=habitos,
        medallas_ganadas=sum(1 for m in medallas if m['desbloqueada']),
        medallas_total=len(medallas),
        min_password=MIN_PASSWORD,
    )


@bp.route('/usuario', methods=['POST'])
@login_required
def cambiar_usuario():
    nuevo = (request.form.get('nuevo_usuario') or '').strip()
    if not nuevo or len(nuevo) > MAX_USUARIO:
        flash(f'Escribe un nombre de usuario (máximo {MAX_USUARIO} caracteres).', 'danger')
    elif nuevo == current_user.nameUser:
        flash('Ese ya es tu nombre de usuario.', 'warning')
    elif not _contrasena_actual_ok():
        pass
    elif User.query.filter(User.nameUser == nuevo, User.idUser != current_user.idUser).first():
        flash('Ese nombre de usuario ya está en uso. Elige otro.', 'danger')
    else:
        current_user.nameUser = nuevo
        db.session.commit()
        flash(f'Listo, ahora tu usuario es "{nuevo}". Úsalo la próxima vez que inicies sesión.', 'success')
    return redirect(url_for('perfil.index'))


@bp.route('/contrasena', methods=['POST'])
@login_required
def cambiar_contrasena():
    nueva = request.form.get('nueva_contrasena') or ''
    confirmar = request.form.get('confirmar_contrasena') or ''
    if not _contrasena_actual_ok():
        pass
    elif len(nueva) < MIN_PASSWORD:
        flash(f'La nueva contraseña debe tener al menos {MIN_PASSWORD} caracteres.', 'danger')
    elif nueva != confirmar:
        flash('La nueva contraseña y su confirmación no coinciden.', 'danger')
    elif current_user.check_password(nueva):
        flash('La nueva contraseña debe ser distinta de la actual.', 'warning')
    else:
        current_user.set_password(nueva)
        db.session.commit()
        flash('Tu contraseña se cambió correctamente.', 'success')
    return redirect(url_for('perfil.index'))


@bp.route('/foto', methods=['POST'])
@login_required
def subir_foto():
    archivo = request.files.get('foto')
    if not archivo or not archivo.filename:
        flash('Elige una imagen para tu foto de perfil.', 'warning')
        return redirect(url_for('perfil.index'))
    extension = os.path.splitext(archivo.filename)[1].lstrip('.').lower()
    if extension not in EXTENSIONES_FOTO:
        flash('La foto debe ser PNG, JPG, GIF o WEBP.', 'danger')
        return redirect(url_for('perfil.index'))
    archivo.seek(0, os.SEEK_END)
    if archivo.tell() > MAX_FOTO_MB * 1024 * 1024:
        flash(f'La foto pesa demasiado. El máximo es {MAX_FOTO_MB} MB.', 'danger')
        return redirect(url_for('perfil.index'))
    archivo.seek(0)

    # Se vuelve a dibujar la imagen: comprueba que sea una imagen real, quita los
    # metadatos (como la ubicación GPS) y la deja cuadrada y liviana
    try:
        with Image.open(archivo.stream) as img:
            img = ImageOps.exif_transpose(img).convert('RGB')
            img = ImageOps.fit(img, (TAMANO_FOTO, TAMANO_FOTO), Image.LANCZOS)
            os.makedirs(carpeta_avatars(), exist_ok=True)
            nombre = f"{current_user.idUser}_{uuid.uuid4().hex}.jpg"
            img.save(os.path.join(carpeta_avatars(), nombre), 'JPEG', quality=88)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        flash('No se pudo leer esa imagen. Prueba con otra.', 'danger')
        return redirect(url_for('perfil.index'))

    borrar_foto(current_user)
    current_user.avatar = nombre
    db.session.commit()
    flash('¡Tu foto de perfil quedó lista!', 'success')
    return redirect(url_for('perfil.index'))


@bp.route('/foto/quitar', methods=['POST'])
@login_required
def quitar_foto():
    borrar_foto(current_user)
    db.session.commit()
    flash('Quitaste tu foto de perfil.', 'info')
    return redirect(url_for('perfil.index'))


@bp.route('/foto')
@login_required
def ver_foto():
    if not current_user.avatar:
        abort(404)
    respuesta = send_from_directory(carpeta_avatars(), current_user.avatar, mimetype='image/jpeg')
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    return respuesta
