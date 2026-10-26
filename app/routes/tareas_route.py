from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.tareas import Tarea
from app import db
from datetime import date, datetime, timedelta
from collections import defaultdict

bp = Blueprint('tareas', __name__, url_prefix='/tareas')

# Hasta cuándo se puede programar una tarea por adelantado
MAX_DIAS_ADELANTE = 365
DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _etiqueta_dia(fecha, hoy):
    if fecha == hoy:
        return 'Hoy'
    if fecha == hoy + timedelta(days=1):
        return 'Mañana'
    return f"{DIAS_SEMANA[fecha.weekday()]} {fecha.strftime('%d/%m/%Y')}"


def _leer_fecha(texto, hoy):
    """Fecha del formulario (AAAA-MM-DD). Vacía = hoy. None si no es válida
    o está fuera del rango permitido (no se programan tareas en el pasado)."""
    if not texto:
        return hoy
    try:
        fecha = date.fromisoformat(texto)
    except ValueError:
        return None
    if fecha < hoy or fecha > hoy + timedelta(days=MAX_DIAS_ADELANTE):
        return None
    return fecha

@bp.route('/')
@login_required
def index():
    hoy = date.today()
    tareas = Tarea.query.filter_by(idUser=current_user.idUser, fecha=hoy).order_by(Tarea.createdAt).all()

    # Tareas programadas (mañana en adelante). En la lista solo se muestran las
    # de mañana; las de días más lejanos se ven como contador en el calendario.
    manana = hoy + timedelta(days=1)
    futuras = Tarea.query.filter(
        Tarea.idUser == current_user.idUser,
        Tarea.fecha > hoy
    ).order_by(Tarea.fecha, Tarea.createdAt).all()
    tareas_manana = [t for t in futuras if t.fecha == manana]

    # Para marcar en el calendario cuántas tareas tiene cada día (hoy en adelante)
    conteos = defaultdict(int)
    for t in futuras:
        conteos[t.fecha.isoformat()] += 1
    if tareas:
        conteos[hoy.isoformat()] = len(tareas)

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

    return render_template(
        'tareas/index.html', tareas=tareas, historial_dias=historial_dias, tareas_manana=tareas_manana, conteos=dict(conteos),
        hoy=hoy.isoformat(), manana=manana.isoformat(),
        fecha_maxima=(hoy + timedelta(days=MAX_DIAS_ADELANTE)).isoformat(),
    )

@bp.route('/add', methods=['POST'])
@login_required
def add():
    descripcion = (request.form.get('descripcion') or '').strip()
    if not descripcion:
        return jsonify({'success': False}), 400
    hoy = date.today()
    fecha = _leer_fecha(request.form.get('fecha'), hoy)
    if fecha is None:
        return jsonify({'success': False, 'error': 'Elige una fecha desde hoy en adelante.'}), 400
    tarea = Tarea(idUser=current_user.idUser, descripcion=descripcion, fecha=fecha)
    db.session.add(tarea)
    db.session.commit()
    return jsonify({
        'success': True, 'id': tarea.idTarea, 'descripcion': tarea.descripcion,
        'fecha': fecha.isoformat(), 'label': _etiqueta_dia(fecha, hoy), 'esHoy': fecha == hoy,
    })

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

@bp.route('/<int:tarea_id>/editar', methods=['POST'])
@login_required
def editar(tarea_id):
    tarea = Tarea.query.filter_by(idTarea=tarea_id, idUser=current_user.idUser).first_or_404()
    descripcion = (request.form.get('descripcion') or '').strip()
    if not descripcion or len(descripcion) > 255:
        return jsonify({'success': False, 'error': 'La tarea no puede quedar vacía.'}), 400
    tarea.descripcion = descripcion
    db.session.commit()
    return jsonify({'success': True, 'descripcion': tarea.descripcion})

@bp.route('/<int:tarea_id>/recordatorio', methods=['POST'])
@login_required
def recordatorio(tarea_id):
    """Pone (hora "HH:MM") o quita (hora vacía) el correo de recordatorio de la tarea."""
    tarea = Tarea.query.filter_by(idTarea=tarea_id, idUser=current_user.idUser).first_or_404()
    hora = (request.form.get('hora') or '').strip()
    if hora:
        try:
            hora = datetime.strptime(hora, '%H:%M').strftime('%H:%M')
        except ValueError:
            return jsonify({'success': False, 'error': 'Elige una hora válida.'}), 400
    tarea.horaRecordatorio = hora or None
    tarea.recordatorioEnviado = False
    db.session.commit()
    return jsonify({
        'success': True, 'hora': tarea.horaRecordatorio, 'horaTexto': tarea.hora_texto(),
        # Sin correo en el perfil no hay a dónde enviarlo: la pantalla lo avisa
        'sinCorreo': not current_user.email,
        'correoActivo': bool(current_app.config.get('MAIL_ENABLED')),
    })
