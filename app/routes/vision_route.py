import os
import uuid
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, send_from_directory, abort,
)
from flask_login import login_required, current_user
from app import db
from app.models.vision_board import (
    MetaVision, CATEGORIAS_META, CLAVES_CATEGORIAS, EXTENSIONES_IMAGEN, TAMANO_MAXIMO_MB,
)

bp = Blueprint('vision', __name__, url_prefix='/vision')

# Primeros bytes de cada tipo de imagen permitido: así no basta con renombrar
# cualquier archivo a .png para subirlo
FIRMAS_IMAGEN = {
    'png': [b'\x89PNG\r\n\x1a\n'],
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'gif': [b'GIF87a', b'GIF89a'],
}


def _meta_del_usuario(meta_id):
    return MetaVision.query.filter_by(idMeta=meta_id, idUser=current_user.idUser).first_or_404()


def _carpeta_imagenes(idUser):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'vision', str(idUser))


def _es_imagen_valida(archivo, extension):
    cabecera = archivo.stream.read(16)
    archivo.stream.seek(0)
    if extension == 'webp':
        return cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP'
    return any(cabecera.startswith(firma) for firma in FIRMAS_IMAGEN.get(extension, []))


# Valores EXIF de orientación en los que la foto está girada 90°: el navegador
# la muestra rotada, así que el ancho y el alto reales van intercambiados
ORIENTACIONES_GIRADAS = {5, 6, 7, 8}


def _medir_imagen(ruta):
    """Devuelve (ancho, alto) tal como se verá la imagen, o None si Pillow no
    puede abrirla (archivo dañado o que no es una imagen)."""
    try:
        with Image.open(ruta) as img:
            ancho, alto = img.size
            if img.getexif().get(0x0112) in ORIENTACIONES_GIRADAS:
                ancho, alto = alto, ancho
            return ancho, alto
    except (UnidentifiedImageError, OSError):
        return None


def _guardar_imagen(archivo):
    """Guarda la imagen subida con un nombre aleatorio y devuelve
    (nombre, ancho, alto), o None si el archivo no es una imagen permitida."""
    if not archivo or not archivo.filename:
        return None
    extension = os.path.splitext(archivo.filename)[1].lstrip('.').lower()
    if extension not in EXTENSIONES_IMAGEN or not _es_imagen_valida(archivo, extension):
        return None
    carpeta = _carpeta_imagenes(current_user.idUser)
    os.makedirs(carpeta, exist_ok=True)
    guardado = f"{uuid.uuid4().hex}.{extension}"
    ruta = os.path.join(carpeta, guardado)
    archivo.save(ruta)
    medidas = _medir_imagen(ruta)
    if not medidas:
        os.remove(ruta)
        return None
    return (guardado, *medidas)


def _completar_medidas(metas):
    """Las metas creadas antes de guardar el tamaño de la imagen lo calculan
    una sola vez aquí."""
    cambios = False
    for meta in metas:
        if meta.ancho and meta.alto:
            continue
        medidas = _medir_imagen(os.path.join(_carpeta_imagenes(meta.idUser), meta.imagen))
        if medidas:
            meta.ancho, meta.alto = medidas
            cambios = True
    if cambios:
        db.session.commit()


def _borrar_imagen(idUser, nombre):
    try:
        os.remove(os.path.join(_carpeta_imagenes(idUser), nombre))
    except FileNotFoundError:
        pass


def _datos_meta_del_form():
    """Lee y valida los campos de texto del formulario de una meta."""
    categoria = request.form.get('categoria')
    fecha = None
    try:
        fecha = datetime.strptime(request.form.get('fechaObjetivo') or '', '%Y-%m-%d').date()
    except ValueError:
        pass
    return {
        'titulo': (request.form.get('titulo') or '').strip()[:120],
        'descripcion': (request.form.get('descripcion') or '').strip()[:500] or None,
        'categoria': categoria if categoria in CLAVES_CATEGORIAS else CLAVES_CATEGORIAS[0],
        'fechaObjetivo': fecha,
    }


@bp.route('/')
@login_required
def index():
    metas = (MetaVision.query.filter_by(idUser=current_user.idUser)
             .order_by(MetaVision.cumplida, MetaVision.createdAt.desc()).all())
    _completar_medidas(metas)
    filtro = request.args.get('categoria')
    if filtro in CLAVES_CATEGORIAS:
        visibles = [m for m in metas if m.categoria == filtro]
    else:
        filtro, visibles = None, metas
    return render_template(
        'vision/index.html',
        metas=visibles,
        total=len(metas),
        cumplidas=sum(1 for m in metas if m.cumplida),
        categorias=CATEGORIAS_META,
        filtro=filtro,
        extensiones=sorted(EXTENSIONES_IMAGEN),
        tamano_maximo_mb=TAMANO_MAXIMO_MB,
    )


@bp.route('/crear', methods=['POST'])
@login_required
def crear():
    datos = _datos_meta_del_form()
    if not datos['titulo']:
        flash('La meta necesita un título.', 'danger')
        return redirect(url_for('vision.index'))
    imagen = _guardar_imagen(request.files.get('imagen'))
    if not imagen:
        flash('Elige una imagen válida (png, jpg, gif o webp) para tu meta.', 'danger')
        return redirect(url_for('vision.index'))
    nombre, ancho, alto = imagen
    db.session.add(MetaVision(idUser=current_user.idUser, imagen=nombre, ancho=ancho, alto=alto, **datos))
    db.session.commit()
    flash(f"Meta '{datos['titulo']}' agregada a tu vision board.", 'success')
    return redirect(url_for('vision.index'))


@bp.route('/<int:meta_id>/editar', methods=['POST'])
@login_required
def editar(meta_id):
    meta = _meta_del_usuario(meta_id)
    datos = _datos_meta_del_form()
    if not datos['titulo']:
        flash('La meta necesita un título.', 'danger')
        return redirect(url_for('vision.index'))
    archivo = request.files.get('imagen')
    if archivo and archivo.filename:
        nueva = _guardar_imagen(archivo)
        if not nueva:
            flash('La imagen no es válida (png, jpg, gif o webp). Se mantuvo la anterior.', 'warning')
        else:
            _borrar_imagen(meta.idUser, meta.imagen)
            meta.imagen, meta.ancho, meta.alto = nueva
    for campo, valor in datos.items():
        setattr(meta, campo, valor)
    db.session.commit()
    flash(f"Meta '{meta.titulo}' actualizada.", 'success')
    return redirect(url_for('vision.index'))


@bp.route('/<int:meta_id>/cumplida', methods=['POST'])
@login_required
def alternar_cumplida(meta_id):
    meta = _meta_del_usuario(meta_id)
    meta.cumplida = not meta.cumplida
    meta.fechaCumplida = datetime.now() if meta.cumplida else None
    db.session.commit()
    if meta.cumplida:
        flash(f"¡Lograste '{meta.titulo}'! 🎉", 'success')
    return redirect(url_for('vision.index'))


@bp.route('/<int:meta_id>/eliminar', methods=['POST'])
@login_required
def eliminar(meta_id):
    meta = _meta_del_usuario(meta_id)
    titulo = meta.titulo
    _borrar_imagen(meta.idUser, meta.imagen)
    db.session.delete(meta)
    db.session.commit()
    flash(f"Meta '{titulo}' eliminada.", 'success')
    return redirect(url_for('vision.index'))


@bp.route('/<int:meta_id>/imagen')
@login_required
def imagen(meta_id):
    meta = _meta_del_usuario(meta_id)
    carpeta = _carpeta_imagenes(meta.idUser)
    if not os.path.exists(os.path.join(carpeta, meta.imagen)):
        abort(404)
    respuesta = send_from_directory(carpeta, meta.imagen)
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    return respuesta
