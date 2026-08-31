from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app import db
from app.gamificacion import get_or_create_progress, aplicar_penalizaciones_pendientes, sincronizar_racha
from app.level_config import NIVEL_MAXIMO, NIVELES, XP_POR_HABITO, PENALIZACION_POR_DIA_PERDIDO, calcular_progreso
from collections import defaultdict
from datetime import datetime, date, timedelta
from math import ceil

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
    hoy = date.today()

    # Años disponibles: los que tienen registros, más el año actual siempre visible
    anios_con_datos = {
        r.fecha.year for r in
        db.session.query(HistHabit.fecha).filter_by(idUser=current_user.idUser).all()
    }
    anios_con_datos.add(hoy.year)
    anios_disponibles = sorted(anios_con_datos, reverse=True)

    anio_param = request.args.get('year', type=int)
    anio_seleccionado = anio_param if anio_param in anios_disponibles else hoy.year

    if anio_seleccionado == hoy.year:
        # Últimas ~53 semanas terminando hoy, igual que GitHub para el año en curso
        inicio = hoy - timedelta(days=370)
        fin = hoy
    else:
        inicio = date(anio_seleccionado, 1, 1)
        fin = date(anio_seleccionado, 12, 31)

    registros = HistHabit.query.filter(
        HistHabit.idUser == current_user.idUser,
        HistHabit.fecha >= inicio,
        HistHabit.fecha <= fin,
    ).all()

    habit_nombres = {
        h.idHabit: h.habitName
        for h in Habit.query.filter_by(idUser=current_user.idUser).all()
    }

    conteo = defaultdict(int)
    nombres_por_dia = defaultdict(list)
    for r in registros:
        conteo[r.fecha] += 1
        nombres_por_dia[r.fecha].append(habit_nombres.get(r.idHabit, 'Hábito eliminado'))

    def nivel_actividad(count):
        if count == 0:
            return 0
        if count == 1:
            return 1
        if count <= 3:
            return 2
        if count <= 6:
            return 3
        return 4

    # Alinear la grilla a semanas completas (Lunes a Domingo)
    inicio_grid = inicio - timedelta(days=inicio.weekday())
    fin_grid = fin + timedelta(days=(6 - fin.weekday()))

    dias = []
    cursor = inicio_grid
    while cursor <= fin_grid:
        count = conteo.get(cursor, 0)
        dias.append({
            'fecha': cursor.isoformat(),
            'label': cursor.strftime('%d/%m/%Y'),
            'count': count,
            'nivel': nivel_actividad(count),
            'habitos': nombres_por_dia.get(cursor, []),
            'es_futuro': cursor > hoy,
        })
        cursor += timedelta(days=1)

    month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    semanas = []
    for i in range(0, len(dias), 7):
        semana_dias = dias[i:i + 7]
        primer_dia = date.fromisoformat(semana_dias[0]['fecha'])
        mes = month_names[primer_dia.month - 1] if primer_dia.day <= 7 else ''
        semanas.append({'dias': semana_dias, 'mes': mes})

    total_actividades = sum(conteo.values())
    dias_activos = len(conteo)

    return render_template(
        'menu/historial.html',
        semanas=semanas,
        total_actividades=total_actividades,
        dias_activos=dias_activos,
        anios_disponibles=anios_disponibles,
        anio_seleccionado=anio_seleccionado,
    )

@bp.route('/nivel')
@login_required
def nivel():
    progress = get_or_create_progress(current_user.idUser)
    penalizado = aplicar_penalizaciones_pendientes(progress)
    racha_actual, racha_maxima = sincronizar_racha(progress)
    db.session.commit()

    progreso = calcular_progreso(progress.xpTotal)

    # ── Tabla completa de niveles (para mostrar el mapa de progresión) ──
    niveles_vista = [
        {
            'nivel': n['nivel'],
            'titulo': n['titulo'],
            'umbral': n['umbral'],
            'alcanzado': progress.xpTotal >= n['umbral'],
            'actual': n['nivel'] == progreso['nivel'],
        }
        for n in NIVELES
    ]

    # ── Qué falta para llegar al nivel máximo ──
    nivel_max_info = NIVELES[-1]
    xp_faltante_max = max(0, nivel_max_info['umbral'] - progress.xpTotal)
    habitos_faltantes_max = ceil(xp_faltante_max / XP_POR_HABITO) if xp_faltante_max > 0 else 0

    data = {
        'nivel': progreso['nivel'],
        'nivel_maximo': NIVEL_MAXIMO,
        'titulo': progreso['titulo'],
        'es_nivel_maximo': progreso['es_nivel_maximo'],
        'xp': progress.xpTotal,
        'xp_en_nivel': progreso['xp_en_nivel'],
        'xp_por_nivel': progreso['xp_por_nivel'],
        'xp_para_subir': progreso['xp_para_subir'],
        'pct_nivel': progreso['pct_nivel'],
        'completados': progress.habitosCompletados,
        'racha_max': racha_maxima,
        'racha_actual': racha_actual,
        'penalizado': penalizado,
        'penalizacion_xp': PENALIZACION_POR_DIA_PERDIDO,
        'niveles': niveles_vista,
        'xp_faltante_max': xp_faltante_max,
        'habitos_faltantes_max': habitos_faltantes_max,
        'nivel_max_titulo': nivel_max_info['titulo'],
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
