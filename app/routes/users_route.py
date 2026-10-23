from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file, flash, abort
from flask_login import login_required, current_user, logout_user
from app.models.users import User
from app import db
from io import BytesIO
import base64
import json

bp = Blueprint('user', __name__, url_prefix='/User')

MIN_PASSWORD = 6


def _own_user_or_403(id):
    """Cada usuario solo puede ver o modificar su propia cuenta."""
    if id != current_user.idUser:
        abort(403)
    return db.get_or_404(User, id)


def _delete_user_data(idUser):
    """Borra todos los datos asociados al usuario (SQLite no aplica las FK en cascada)."""
    from app.models.hist_habits import HistHabit
    from app.models.habitos import Habit
    from app.models.ruleta_castigo import Castigo
    from app.models.tareas import Tarea
    from app.models.user_progress import UserProgress
    from app.models.vocabulario_registro import VocabularioRegistro
    from app.models.vocabulario import Vocabulario
    from app.models.shadowing_sesion import ShadowingSesion
    from app.models.metodo_estudio import MetodoEstudio
    from app.models.recordatorios import Recordatorio
    from app.routes.metodos_route import _borrar_archivos
    for metodo in MetodoEstudio.query.filter_by(idUser=idUser).all():
        _borrar_archivos([a for t in metodo.tarjetas for a in t.apuntes])
        db.session.delete(metodo)  # en cascada: tarjetas del Kanban y apuntes
    for model in (HistHabit, Habit, Castigo, Tarea, UserProgress,
                  VocabularioRegistro, Vocabulario, ShadowingSesion, Recordatorio):
        model.query.filter_by(idUser=idUser).delete(synchronize_session=False)


@bp.route('/')
@login_required
def index():
    # Solo se lista la cuenta propia (antes se mostraban todos los usuarios y sus contraseñas)
    data = [current_user]
    return render_template('users/index.html', data=data)


@bp.route('/js')
@login_required
def indexjs():
    return jsonify([current_user.to_dict()])


@bp.route('/add', methods=['GET', 'POST'])
def add():
    """Registro público de cuentas nuevas (lo usa la pantalla de login)."""
    if request.method == 'POST':
        nameUser = (request.form.get('nameUser') or '').strip()
        passwordUser = request.form.get('passwordUser') or ''

        if not nameUser or len(nameUser) > 80:
            flash("Ingresa un nombre de usuario válido (máx. 80 caracteres).", "danger")
            return redirect(url_for('auth.login', register=1))
        if len(passwordUser) < MIN_PASSWORD:
            flash(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", "danger")
            return redirect(url_for('auth.login', register=1))

        existing_user = User.query.filter_by(nameUser=nameUser).first()
        if existing_user:
            flash("El usuario ya está en uso, ingrese otro usuario.", "danger")
            return redirect(url_for('auth.login', register=1))

        new_user = User(nameUser=nameUser, password=passwordUser)
        db.session.add(new_user)
        db.session.commit()

        flash("Cuenta creada exitosamente. Por favor inicia sesión.", "success")
        return redirect(url_for('auth.login'))
    return render_template('users/add.html')


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    user = _own_user_or_403(id)
    if request.method == 'POST':
        nameUser = (request.form.get('nameUser') or '').strip()
        passwordUser = request.form.get('passwordUser') or ''

        if nameUser and nameUser != user.nameUser:
            if User.query.filter(User.nameUser == nameUser, User.idUser != user.idUser).first():
                flash("Ese nombre de usuario ya está en uso.", "danger")
                return redirect(url_for('user.edit', id=id))
            user.nameUser = nameUser

        # Contraseña vacía = no cambiarla
        if passwordUser:
            if len(passwordUser) < MIN_PASSWORD:
                flash(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", "danger")
                return redirect(url_for('user.edit', id=id))
            user.set_password(passwordUser)

        db.session.commit()
        flash("Cuenta actualizada.", "success")
        return redirect(url_for('user.index'))

    return render_template('users/edit.html', user=user)


@bp.route('/detail/<int:id>')
@login_required
def detail(id):
    user = _own_user_or_403(id)
    return render_template('users/detail.html', user=user)


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    user = _own_user_or_403(id)
    from app.routes.perfil_route import borrar_foto
    borrar_foto(user)
    _delete_user_data(user.idUser)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash("Tu cuenta fue eliminada.", "info")
    return redirect(url_for('auth.login'))


@bp.route('/qr/<int:id>')
@login_required
def generate_qr(id):
    user = _own_user_or_403(id)
    qr_code_img = base64.b64decode(user.generate_qr())
    return send_file(BytesIO(qr_code_img), mimetype='image/png')


@bp.route('/read_qr', methods=['POST'])
@login_required
def read_qr():
    try:
        from pyzbar.pyzbar import decode
    except ImportError:
        return "La lectura de QR en el servidor requiere instalar 'pyzbar' (y la librería zbar del sistema).", 501
    from PIL import Image

    if 'qr_image' not in request.files:
        return "No se ha proporcionado una imagen de QR", 400

    try:
        img = Image.open(request.files['qr_image'])
        decoded_objects = decode(img)
    except Exception:
        return "La imagen no es válida", 400

    if not decoded_objects:
        return "No se pudo leer el código QR", 400

    try:
        user_data = json.loads(decoded_objects[0].data.decode('utf-8'))
        user_id = int(user_data.get('ID'))
    except (ValueError, TypeError, AttributeError):
        return "El código QR no contiene un ID de usuario válido", 400

    user = _own_user_or_403(user_id)
    return render_template('users/detail.html', user=user)
