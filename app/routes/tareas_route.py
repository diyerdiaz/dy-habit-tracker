from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.tareas import Tarea
from app import db
from datetime import date
from collections import defaultdict

bp = Blueprint('tareas', __name__, url_prefix='/tareas')

@bp.route('/')
@login_required
def index():
    hoy = date.today()
    tareas = Tarea.query.filter_by(idUser=current_user.idUser, fecha=hoy).order_by(Tarea.createdAt).all()

    # Historial: tareas de días anteriores, agrupadas por fecha
    historial_raw = Tarea.query.filter(
        Tarea.idUser == current_user.idUser,
        Tarea.fecha < hoy
    ).order_by(Tarea.fecha.desc(), Tarea.createdAt).all()

    agrupado = defaultdict(list)
    for t in historial_raw:
        agrupado[t.fecha].append(t)

    historial_dias = [
        {
            'label': fecha.strftime('%d/%m/%Y'),
            'total': len(items),
            'completadas': sum(1 for t in items if t.completada),
            'tareas': items,
        }
        for fecha, items in agrupado.items()
    ]

    return render_template('tareas/index.html', tareas=tareas, historial_dias=historial_dias)

@bp.route('/add', methods=['POST'])
@login_required
def add():
    descripcion = (request.form.get('descripcion') or '').strip()
    if not descripcion:
        return jsonify({'success': False}), 400
    tarea = Tarea(idUser=current_user.idUser, descripcion=descripcion, fecha=date.today())
    db.session.add(tarea)
    db.session.commit()
    return jsonify({'success': True, 'id': tarea.idTarea, 'descripcion': tarea.descripcion})

@bp.route('/<int:tarea_id>/toggle', methods=['POST'])
@login_required
def toggle(tarea_id):
    tarea = Tarea.query.filter_by(idTarea=tarea_id, idUser=current_user.idUser).first_or_404()
    tarea.completada = not tarea.completada
    db.session.commit()
    return jsonify({'success': True, 'completada': tarea.completada})

@bp.route('/<int:tarea_id>/delete', methods=['POST'])
@login_required
def delete(tarea_id):
    tarea = Tarea.query.filter_by(idTarea=tarea_id, idUser=current_user.idUser).first_or_404()
    db.session.delete(tarea)
    db.session.commit()
    return jsonify({'success': True})
