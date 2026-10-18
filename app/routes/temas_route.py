from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.temas import (
    TemaExplicar, SesionExplicacion, TIEMPOS_MINUTOS, MINUTOS_MAXIMOS, TEMAS_SUGERIDOS, elegir_tema,
)

bp = Blueprint('temas', __name__, url_prefix='/temas')


def _tema_del_usuario(tema_id):
    return TemaExplicar.query.filter_by(idTema=tema_id, idUser=current_user.idUser).first_or_404()


def _temas_del_usuario():
    return TemaExplicar.query.filter_by(idUser=current_user.idUser).order_by(TemaExplicar.createdAt).all()


def _temas_pendientes():
    """Los temas que todavía no se han explicado: son los únicos que salen en la ruleta."""
    return [t for t in _temas_del_usuario() if not t.estudiado]


@bp.route('/')
@login_required
def index():
    todos = _temas_del_usuario()
    temas = [t for t in todos if not t.estudiado]
    estudiados = sorted((t for t in todos if t.estudiado), key=lambda t: t.fechaEstudiado or t.createdAt, reverse=True)
    sesiones = (SesionExplicacion.query.filter_by(idUser=current_user.idUser)
                .order_by(SesionExplicacion.fecha.desc()).limit(8).all())
    total_sesiones, total_segundos = (db.session.query(
        func.count(SesionExplicacion.idSesion), func.coalesce(func.sum(SesionExplicacion.segundosHablados), 0))
        .filter(SesionExplicacion.idUser == current_user.idUser).one())
    return render_template(
        'temas/index.html',
        temas=temas,
        estudiados=estudiados,
        sesiones=sesiones,
        total_sesiones=total_sesiones,
        total_minutos=round(total_segundos / 60),
        tiempos=TIEMPOS_MINUTOS,
        minutos_maximos=MINUTOS_MAXIMOS,
    )


@bp.route('/crear', methods=['POST'])
@login_required
def crear():
    """Agrega uno o varios temas: cada línea del cuadro de texto es un tema.
    Si se escribe uno que ya se había explicado, vuelve a la lista."""
    existentes = {t.titulo.lower(): t for t in _temas_del_usuario()}
    nuevos = 0
    for linea in (request.form.get('titulos') or '').splitlines():
        titulo = linea.strip()[:150]
        if not titulo:
            continue
        previo = existentes.get(titulo.lower())
        if previo is None:
            existentes[titulo.lower()] = TemaExplicar(idUser=current_user.idUser, titulo=titulo)
            db.session.add(existentes[titulo.lower()])
            nuevos += 1
        elif previo.estudiado:
            previo.estudiado, previo.fechaEstudiado = False, None
            nuevos += 1
    db.session.commit()
    if nuevos:
        flash(f"{nuevos} {'tema agregado' if nuevos == 1 else 'temas agregados'}.", 'success')
    else:
        flash('Escribe al menos un tema nuevo (uno por línea).', 'warning')
    return redirect(url_for('temas.index'))


@bp.route('/sugeridos', methods=['POST'])
@login_required
def agregar_sugeridos():
    existentes = {t.titulo.lower() for t in _temas_del_usuario()}
    for titulo in TEMAS_SUGERIDOS:
        if titulo.lower() not in existentes:
            db.session.add(TemaExplicar(idUser=current_user.idUser, titulo=titulo))
    db.session.commit()
    flash('Se agregaron los temas sugeridos.', 'success')
    return redirect(url_for('temas.index'))


@bp.route('/<int:tema_id>/editar', methods=['POST'])
@login_required
def editar(tema_id):
    tema = _tema_del_usuario(tema_id)
    titulo = (request.form.get('titulo') or '').strip()[:150]
    if not titulo:
        flash('El tema necesita un título.', 'danger')
        return redirect(url_for('temas.index'))
    tema.titulo = titulo
    tema.notas = (request.form.get('notas') or '').strip()[:500] or None
    db.session.commit()
    flash(f"Tema '{tema.titulo}' actualizado.", 'success')
    return redirect(url_for('temas.index'))


@bp.route('/<int:tema_id>/restaurar', methods=['POST'])
@login_required
def restaurar(tema_id):
    """Devuelve a la lista un tema ya explicado, para practicarlo otra vez."""
    tema = _tema_del_usuario(tema_id)
    tema.estudiado, tema.fechaEstudiado = False, None
    db.session.commit()
    flash(f"'{tema.titulo}' volvió a tu lista de temas.", 'success')
    return redirect(url_for('temas.index'))


@bp.route('/<int:tema_id>/eliminar', methods=['POST'])
@login_required
def eliminar(tema_id):
    tema = _tema_del_usuario(tema_id)
    titulo = tema.titulo
    db.session.delete(tema)
    db.session.commit()
    flash(f"Tema '{titulo}' eliminado.", 'success')
    return redirect(url_for('temas.index'))


@bp.route('/girar', methods=['POST'])
@login_required
def girar():
    """Saca un tema al azar (distinto del último) y lo cuenta como salido.
    Solo entre los que aún no se han explicado."""
    temas = _temas_pendientes()
    tema = elegir_tema(temas, session.get('ultimo_tema'))
    if not tema:
        return jsonify({'success': False, 'error': 'No te quedan temas por explicar. Agrega más o vuelve a poner alguno.'}), 400
    tema.vecesSalido += 1
    tema.ultimaVez = datetime.now()
    db.session.commit()
    session['ultimo_tema'] = tema.idTema
    return jsonify({
        'success': True,
        'tema': {'id': tema.idTema, 'titulo': tema.titulo, 'notas': tema.notas or ''},
        # nombres para la animación de la ruleta
        'opciones': [t.titulo for t in temas],
    })


@bp.route('/sesion', methods=['POST'])
@login_required
def guardar_sesion():
    """Guarda una explicación terminada. Recibe JSON:
    {"tema": id, "objetivo": segundos, "hablados": segundos, "calificacion": 1-5}."""
    data = request.get_json(silent=True) or {}
    tema = _tema_del_usuario(int(data.get('tema') or 0))
    try:
        objetivo = int(data.get('objetivo'))
        hablados = int(data.get('hablados'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Tiempo no válido.'}), 400
    limite = MINUTOS_MAXIMOS * 60
    if not (0 < objetivo <= limite) or not (0 <= hablados <= limite):
        return jsonify({'success': False, 'error': 'Tiempo no válido.'}), 400
    calificacion = data.get('calificacion')
    calificacion = calificacion if calificacion in (1, 2, 3, 4, 5) else None
    db.session.add(SesionExplicacion(
        idTema=tema.idTema, idUser=current_user.idUser,
        segundosObjetivo=objetivo, segundosHablados=hablados, calificacion=calificacion,
    ))
    # Ya lo explicó: sale de la lista y de la ruleta
    tema.estudiado, tema.fechaEstudiado = True, datetime.now()
    db.session.commit()
    flash(f"¡Explicaste '{tema.titulo}'! Ya salió de tu lista de temas.", 'success')
    return jsonify({'success': True})
