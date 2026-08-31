from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.habitos import Habit
from app import db
from collections import defaultdict
from datetime import datetime, timedelta

bp = Blueprint('menu', __name__, url_prefix='/menu')

@bp.route('/estadisticas')
@login_required
def estadisticas():
    habits = Habit.query.filter_by(idUser=current_user.idUser).all()

    # ── Tarjetas Resumen ──
    total = len(habits)
    activos = sum(1 for h in habits if h.habitState == 'Activo')
    completados = sum(1 for h in habits if h.habitState == 'Completado')
    pausados = sum(1 for h in habits if h.habitState == 'Pausado')
    pct_cumplimiento = round((completados / total * 100) if total > 0 else 0)

    # Días registrados: rango desde el primer hábito hasta hoy
    fechas = [h.createdAt for h in habits]
    if fechas:
        dias_registrados = (datetime.utcnow() - min(fechas)).days + 1
    else:
        dias_registrados = 0

    # Racha más larga (días consecutivos con al menos un hábito creado)
    dias_con_habito = sorted(set(h.createdAt.date() for h in habits))
    racha_max = racha_actual = 0
    for i, dia in enumerate(dias_con_habito):
        if i == 0 or (dia - dias_con_habito[i-1]).days == 1:
            racha_actual += 1
            racha_max = max(racha_max, racha_actual)
        else:
            racha_actual = 1

    # ── Radar por Categoría (activos por categoría) ──
    categorias = ['salud', 'mente', 'finanzas', 'espiritual']
    radar_labels = ['Salud y Deporte', 'Mente y Educación', 'Finanzas', 'Espiritual/Social']
    cat_count = defaultdict(int)
    for h in habits:
        if h.habitState == 'Activo':
            cat_count[h.habitCategory] += 1
    radar_data = [cat_count.get(c, 0) for c in categorias]

    # ── Barras: hábitos creados por día (últimos 7 días) ──
    today = datetime.utcnow().date()
    week_labels = []
    week_data = []
    day_names = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        week_labels.append(day_names[day.weekday()])
        count = sum(1 for h in habits if h.createdAt.date() == day)
        week_data.append(count)

    # ── Línea: cumplimiento acumulado por semana (últimas 6 semanas) ──
    line_labels = []
    line_data = []
    for i in range(5, -1, -1):
        inicio = today - timedelta(weeks=i+1)
        fin = today - timedelta(weeks=i)
        semana_habits = [h for h in habits if inicio <= h.createdAt.date() < fin]
        completados_sem = sum(1 for h in semana_habits if h.habitState == 'Completado')
        total_sem = len(semana_habits)
        pct = round((completados_sem / total_sem * 100) if total_sem > 0 else 0)
        line_labels.append(f"Sem {6 - i}")
        line_data.append(pct)

    stats = {
        'total': total,
        'activos': activos,
        'completados': completados,
        'pausados': pausados,
        'pct_cumplimiento': pct_cumplimiento,
        'dias_registrados': dias_registrados,
        'racha_max': racha_max,
        'radar_labels': radar_labels,
        'radar_data': radar_data,
        'week_labels': week_labels,
        'week_data': week_data,
        'line_labels': line_labels,
        'line_data': line_data,
    }

    return render_template('menu/estadisticas.html', stats=stats)

@bp.route('/historial')
@login_required
def historial():
    return render_template('menu/historial.html')

@bp.route('/nivel')
@login_required
def nivel():
    habits = Habit.query.filter_by(idUser=current_user.idUser).all()
    completados = sum(1 for h in habits if h.habitState == 'Completado')

    dias_con_habito = sorted(set(h.createdAt.date() for h in habits))
    racha_max = racha_actual = 0
    for i, dia in enumerate(dias_con_habito):
        if i == 0 or (dia - dias_con_habito[i - 1]).days == 1:
            racha_actual += 1
            racha_max = max(racha_max, racha_actual)
        else:
            racha_actual = 1

    xp_por_nivel = 100
    xp = completados * 15 + racha_max * 5
    nivel_actual = xp // xp_por_nivel + 1
    xp_en_nivel = xp % xp_por_nivel
    pct_nivel = round((xp_en_nivel / xp_por_nivel) * 100)

    titulos = ['Novato', 'Aprendiz', 'Constante', 'Disciplinado', 'Enfocado',
               'Estratega', 'Maestro de Hábitos', 'Leyenda']
    titulo = titulos[min(nivel_actual - 1, len(titulos) - 1)]

    data = {
        'nivel': nivel_actual,
        'titulo': titulo,
        'xp': xp,
        'xp_en_nivel': xp_en_nivel,
        'xp_por_nivel': xp_por_nivel,
        'xp_para_subir': xp_por_nivel - xp_en_nivel,
        'pct_nivel': pct_nivel,
        'completados': completados,
        'racha_max': racha_max,
    }
    return render_template('menu/nivel.html', data=data)

from app.models.ruleta_castigo import Castigo
from app.models.habitos import Habit as HabitModel

@bp.route('/castigo/<int:castigo_id>/completar', methods=['POST'])
@login_required
def castigo_completar(castigo_id):
    castigo = Castigo.query.filter_by(idCastigo=castigo_id, idUser=current_user.idUser).first_or_404()
    castigo.castigoState = 'Completado'
    db.session.commit()
    return jsonify({'success': True, 'name': castigo.castigoName})

@bp.route('/ruleta')
@login_required
def ruleta():
    castigos = [c.to_dict() for c in Castigo.query.filter_by(idUser=current_user.idUser).all()]
    habits = [h.to_dict() for h in HabitModel.query.filter_by(idUser=current_user.idUser).all()]
    return render_template('menu/ruleta.html', habits=habits, castigos=castigos)
