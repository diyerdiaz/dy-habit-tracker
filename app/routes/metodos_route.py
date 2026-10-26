import os
import uuid
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify,
    send_from_directory, abort,
)
from flask_login import login_required, current_user
from app import db
from app.services.archivos import carpeta_apuntes, borrar_apuntes
from app.models.metodo_estudio import (
    MetodoEstudio, KanbanTarjeta, Apunte, COLUMNAS_KANBAN, CLAVES_COLUMNAS,
    ICONOS_METODO, COLORES_METODO, METODOS_SUGERIDOS,
    EXTENSIONES_APUNTES, EXTENSIONES_EN_LINEA, TAMANO_MAXIMO_MB,
)

bp = Blueprint('metodos', __name__, url_prefix='/metodos')


def _metodo_del_usuario(metodo_id):
    return MetodoEstudio.query.filter_by(idMetodo=metodo_id, idUser=current_user.idUser).first_or_404()


def _tarjeta_del_usuario(tarjeta_id):
    return KanbanTarjeta.query.filter_by(idTarjeta=tarjeta_id, idUser=current_user.idUser).first_or_404()


def _datos_metodo_del_form():
    """Lee y valida los campos del formulario de un método."""
    nombre = (request.form.get('nombre') or '').strip()[:120]
    descripcion = (request.form.get('descripcion') or '').strip()[:500]
    icono = request.form.get('icono')
    color = request.form.get('color')
    return {
        'nombre': nombre,
        'descripcion': descripcion or None,
        'icono': icono if icono in ICONOS_METODO else 'bi-book',
        'color': color if color in COLORES_METODO else COLORES_METODO[0],
    }


# Si llega otra creación idéntica en este lapso, es un doble clic: se ignora
VENTANA_DUPLICADO = timedelta(seconds=10)


def _recien_creado(modelo, **filtros):
    """True si el usuario creó hace segundos un registro con los mismos datos."""
    limite = datetime.now() - VENTANA_DUPLICADO
    return modelo.query.filter_by(idUser=current_user.idUser, **filtros).filter(modelo.createdAt >= limite).first() is not None


# ── Tarjetas de métodos ──

@bp.route('/')
@login_required
def index():
    metodos = MetodoEstudio.query.filter_by(idUser=current_user.idUser).order_by(MetodoEstudio.createdAt).all()
    return render_template(
        'metodos/index.html',
        metodos=metodos,
        iconos=ICONOS_METODO,
        colores=COLORES_METODO,
    )


@bp.route('/crear', methods=['POST'])
@login_required
def crear():
    datos = _datos_metodo_del_form()
    if not datos['nombre']:
        flash('El método necesita un nombre.', 'danger')
        return redirect(url_for('metodos.index'))
    if _recien_creado(MetodoEstudio, nombre=datos['nombre']):
        return redirect(url_for('metodos.index'))
    db.session.add(MetodoEstudio(idUser=current_user.idUser, **datos))
    db.session.commit()
    flash(f"Método '{datos['nombre']}' agregado.", 'success')
    return redirect(url_for('metodos.index'))


@bp.route('/sugeridos', methods=['POST'])
@login_required
def agregar_sugeridos():
    existentes = {m.nombre for m in MetodoEstudio.query.filter_by(idUser=current_user.idUser).all()}
    for sugerido in METODOS_SUGERIDOS:
        if sugerido['nombre'] not in existentes:
            db.session.add(MetodoEstudio(idUser=current_user.idUser, **sugerido))
    db.session.commit()
    flash('Se agregaron los métodos sugeridos.', 'success')
    return redirect(url_for('metodos.index'))


@bp.route('/<int:metodo_id>/editar', methods=['POST'])
@login_required
def editar(metodo_id):
    metodo = _metodo_del_usuario(metodo_id)
    datos = _datos_metodo_del_form()
    if not datos['nombre']:
        flash('El método necesita un nombre.', 'danger')
        return redirect(request.referrer or url_for('metodos.index'))
    for campo, valor in datos.items():
        setattr(metodo, campo, valor)
    db.session.commit()
    flash(f"Método '{metodo.nombre}' actualizado.", 'success')
    return redirect(request.referrer or url_for('metodos.index'))


@bp.route('/<int:metodo_id>/eliminar', methods=['POST'])
@login_required
def eliminar(metodo_id):
    metodo = _metodo_del_usuario(metodo_id)
    nombre = metodo.nombre
    borrar_apuntes([a for t in metodo.tarjetas for a in t.apuntes])
    db.session.delete(metodo)  # borra también sus tarjetas del tablero y sus apuntes
    db.session.commit()
    flash(f"Método '{nombre}' eliminado.", 'success')
    return redirect(url_for('metodos.index'))


# ── Tablero Kanban de un método ──

@bp.route('/<int:metodo_id>')
@login_required
def tablero(metodo_id):
    metodo = _metodo_del_usuario(metodo_id)
    columnas = [
        {**col, 'tarjetas': [t for t in metodo.tarjetas if t.columna == col['clave']]}
        for col in COLUMNAS_KANBAN
    ]
    return render_template(
        'metodos/tablero.html',
        metodo=metodo,
        columnas=columnas,
        iconos=ICONOS_METODO,
        colores=COLORES_METODO,
        extensiones=sorted(EXTENSIONES_APUNTES),
        tamano_maximo_mb=TAMANO_MAXIMO_MB,
    )


@bp.route('/<int:metodo_id>/tarjetas/crear', methods=['POST'])
@login_required
def tarjeta_crear(metodo_id):
    metodo = _metodo_del_usuario(metodo_id)
    titulo = (request.form.get('titulo') or '').strip()[:150]
    columna = request.form.get('columna')
    if not titulo:
        flash('La tarjeta necesita un título.', 'danger')
        return redirect(url_for('metodos.tablero', metodo_id=metodo.idMetodo))
    columna = columna if columna in CLAVES_COLUMNAS else 'pendiente'
    if _recien_creado(KanbanTarjeta, idMetodo=metodo.idMetodo, titulo=titulo, columna=columna):
        return redirect(url_for('metodos.tablero', metodo_id=metodo.idMetodo))
    ultimo = max((t.orden for t in metodo.tarjetas if t.columna == columna), default=-1)
    db.session.add(KanbanTarjeta(
        idMetodo=metodo.idMetodo,
        idUser=current_user.idUser,
        titulo=titulo,
        descripcion=(request.form.get('descripcion') or '').strip()[:500] or None,
        columna=columna,
        orden=ultimo + 1,
    ))
    db.session.commit()
    return redirect(url_for('metodos.tablero', metodo_id=metodo.idMetodo))


@bp.route('/tarjetas/<int:tarjeta_id>/editar', methods=['POST'])
@login_required
def tarjeta_editar(tarjeta_id):
    tarjeta = _tarjeta_del_usuario(tarjeta_id)
    titulo = (request.form.get('titulo') or '').strip()[:150]
    if titulo:
        tarjeta.titulo = titulo
        tarjeta.descripcion = (request.form.get('descripcion') or '').strip()[:500] or None
        db.session.commit()
    else:
        flash('La tarjeta necesita un título.', 'danger')
    return redirect(url_for('metodos.tablero', metodo_id=tarjeta.idMetodo))


@bp.route('/tarjetas/<int:tarjeta_id>/eliminar', methods=['POST'])
@login_required
def tarjeta_eliminar(tarjeta_id):
    tarjeta = _tarjeta_del_usuario(tarjeta_id)
    metodo_id = tarjeta.idMetodo
    borrar_apuntes(tarjeta.apuntes)
    db.session.delete(tarjeta)
    db.session.commit()
    return redirect(url_for('metodos.tablero', metodo_id=metodo_id))


@bp.route('/tarjetas/<int:tarjeta_id>/mover', methods=['POST'])
@login_required
def tarjeta_mover(tarjeta_id):
    """Mueve una tarjeta a otra columna (arrastrando o con las flechas).
    Recibe JSON: {"columna": "progreso", "orden": [ids de esa columna en orden]}."""
    tarjeta = _tarjeta_del_usuario(tarjeta_id)
    data = request.get_json(silent=True) or {}
    columna = data.get('columna')
    if columna not in CLAVES_COLUMNAS:
        return jsonify({'success': False, 'error': 'Columna no válida.'}), 400

    tarjeta.columna = columna
    orden = data.get('orden') or []
    tarjetas_metodo = {t.idTarjeta: t for t in tarjeta.metodo.tarjetas}
    posicion = 0
    for id_tarjeta in orden:
        t = tarjetas_metodo.get(int(id_tarjeta)) if str(id_tarjeta).isdigit() else None
        if t and t.columna == columna:
            t.orden = posicion
            posicion += 1
    if tarjeta.idTarjeta not in [int(i) for i in orden if str(i).isdigit()]:
        tarjeta.orden = posicion
    db.session.commit()
    return jsonify({'success': True, 'conteo': tarjeta.metodo.conteo_por_columna()})


# ── Apuntes de las tarjetas terminadas ──

@bp.route('/tarjetas/<int:tarjeta_id>/apuntes', methods=['POST'])
@login_required
def apunte_subir(tarjeta_id):
    tarjeta = _tarjeta_del_usuario(tarjeta_id)
    volver = redirect(url_for('metodos.tablero', metodo_id=tarjeta.idMetodo))
    if tarjeta.columna != 'hecho':
        flash('Solo puedes subir apuntes cuando la tarjeta está en "Hecho".', 'warning')
        return volver

    archivos = [a for a in request.files.getlist('archivos') if a and a.filename]
    if not archivos:
        flash('Elige al menos un archivo.', 'warning')
        return volver

    carpeta = carpeta_apuntes(current_user.idUser)
    os.makedirs(carpeta, exist_ok=True)
    subidos, rechazados = 0, []
    for archivo in archivos:
        nombre = os.path.basename(archivo.filename)[:255]
        extension = os.path.splitext(nombre)[1].lstrip('.').lower()
        if extension not in EXTENSIONES_APUNTES:
            rechazados.append(nombre)
            continue
        # Nombre aleatorio en disco: evita choques y rutas manipuladas
        guardado = f"{uuid.uuid4().hex}.{extension}"
        ruta = os.path.join(carpeta, guardado)
        archivo.save(ruta)
        db.session.add(Apunte(
            idTarjeta=tarjeta.idTarjeta,
            idUser=current_user.idUser,
            nombreOriginal=nombre,
            nombreGuardado=guardado,
            tamano=os.path.getsize(ruta),
        ))
        subidos += 1
    db.session.commit()

    if subidos:
        flash(f"{subidos} {'apunte subido' if subidos == 1 else 'apuntes subidos'} a '{tarjeta.titulo}'.", 'success')
    if rechazados:
        flash(f"No se subieron (tipo no permitido): {', '.join(rechazados)}", 'danger')
    return volver


@bp.route('/apuntes/<int:apunte_id>')
@login_required
def apunte_ver(apunte_id):
    apunte = Apunte.query.filter_by(idApunte=apunte_id, idUser=current_user.idUser).first_or_404()
    if not os.path.exists(os.path.join(carpeta_apuntes(apunte.idUser), apunte.nombreGuardado)):
        abort(404)
    descargar = request.args.get('descargar') == '1' or apunte.extension not in EXTENSIONES_EN_LINEA
    respuesta = send_from_directory(
        carpeta_apuntes(apunte.idUser), apunte.nombreGuardado,
        as_attachment=descargar, download_name=apunte.nombreOriginal,
    )
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    return respuesta


@bp.route('/apuntes/<int:apunte_id>/eliminar', methods=['POST'])
@login_required
def apunte_eliminar(apunte_id):
    apunte = Apunte.query.filter_by(idApunte=apunte_id, idUser=current_user.idUser).first_or_404()
    metodo_id = apunte.tarjeta.idMetodo
    borrar_apuntes([apunte])
    db.session.delete(apunte)
    db.session.commit()
    flash(f"Apunte '{apunte.nombreOriginal}' eliminado.", 'success')
    return redirect(url_for('metodos.tablero', metodo_id=metodo_id))
