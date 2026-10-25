from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.vocabulario import Vocabulario
from app.models.vocabulario_registro import VocabularioRegistro
from app.models.shadowing_sesion import ShadowingSesion
from app import db
from app.services.gamificacion import get_or_create_progress, aplicar_penalizaciones_pendientes, sincronizar_racha, calcular_racha
from app.services.level_config import NIVEL_MAXIMO, NIVELES, XP_POR_HABITO, PENALIZACION_POR_DIA_PERDIDO, calcular_progreso
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
        dias_registrados = (datetime.now() - min(fechas)).days + 1
    else:
        dias_registrados = 0

    # Racha más larga: días consecutivos con al menos un hábito CUMPLIDO
    _, racha_max = calcular_racha(current_user.idUser)

    # ── Radar por Categoría (activos por categoría) ──
    categorias = ['salud', 'mente', 'finanzas', 'espiritual']
    radar_labels = ['Salud y Deporte', 'Mente y Educación', 'Finanzas', 'Espiritual/Social']
    cat_count = defaultdict(int)
    for h in habits:
        if h.habitState == 'Activo':
            cat_count[h.habitCategory] += 1
    radar_data = [cat_count.get(c, 0) for c in categorias]

    # ── Barras: hábitos creados por día (últimos 7 días) ──
    today = datetime.now().date()
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

    habitos_creados = Habit.query.filter_by(idUser=current_user.idUser).count()
    progreso = calcular_progreso(progress.xpTotal, habitos_creados)

    # ── Tabla completa de niveles (para mostrar el mapa de progresión) ──
    niveles_vista = [
        {
            'nivel': n['nivel'],
            'titulo': n['titulo'],
            'umbral': n['umbral'],
            'habitos_requeridos': n['nivel'],
            'xp_ok': progress.xpTotal >= n['umbral'],
            'habitos_ok': habitos_creados >= n['nivel'],
            'alcanzado': progress.xpTotal >= n['umbral'] and habitos_creados >= n['nivel'],
            'actual': n['nivel'] == progreso['nivel'],
        }
        for n in NIVELES
    ]

    # ── Qué falta para llegar al nivel máximo (XP y hábitos creados) ──
    nivel_max_info = NIVELES[-1]
    xp_faltante_max = max(0, nivel_max_info['umbral'] - progress.xpTotal)
    habitos_completados_faltantes_max = ceil(xp_faltante_max / XP_POR_HABITO) if xp_faltante_max > 0 else 0
    habitos_creados_faltantes_max = max(0, NIVEL_MAXIMO - habitos_creados)

    data = {
        'nivel': progreso['nivel'],
        'nivel_maximo': NIVEL_MAXIMO,
        'titulo': progreso['titulo'],
        'es_nivel_maximo': progreso['es_nivel_maximo'],
        'xp': progress.xpTotal,
        'xp_en_nivel': progreso['xp_en_nivel'],
        'xp_por_nivel': progreso['xp_por_nivel'],
        'xp_para_subir': progreso['xp_para_subir'],
        'habitos_para_subir': progreso['habitos_para_subir'],
        'bloqueado_por_habitos': progreso['bloqueado_por_habitos'],
        'pct_nivel': progreso['pct_nivel'],
        'completados': progress.habitosCompletados,
        'habitos_creados': habitos_creados,
        'racha_max': racha_maxima,
        'racha_actual': racha_actual,
        'penalizado': penalizado,
        'penalizacion_xp': PENALIZACION_POR_DIA_PERDIDO,
        'niveles': niveles_vista,
        'xp_faltante_max': xp_faltante_max,
        'habitos_creados_faltantes_max': habitos_creados_faltantes_max,
        'habitos_completados_faltantes_max': habitos_completados_faltantes_max,
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

def get_letras_flotantes(id_user):
    """Palabras del usuario para el fondo animado de la sección Inglés.
    Si aún no tiene vocabulario agregado, usa un set genérico por defecto."""
    nombres = [p.nombre for p in Vocabulario.query.filter_by(idUser=id_user).all()]
    if not nombres:
        nombres = ['Hello', 'ABC', 'Learn', 'Yes', 'Go', 'Book', 'Fast', 'Easy', 'Words', 'English']

    letras = []
    i = 0
    while len(letras) < 10:
        letras.append(nombres[i % len(nombres)])
        i += 1
    return letras

@bp.route('/ingles')
@login_required
def ingles():
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template('menu/ingles.html', letras_flotantes=letras_flotantes)

@bp.route('/ingles/shadowing')
@login_required
def shadowing():
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template('menu/shadowing.html', letras_flotantes=letras_flotantes)

@bp.route('/ingles/shadowing/temporizador')
@login_required
def shadowing_temporizador():
    sesiones = ShadowingSesion.query.filter_by(idUser=current_user.idUser).order_by(ShadowingSesion.fecha.desc()).all()
    total_segundos = sum(s.duracionSegundos for s in sesiones)
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template(
        'menu/shadowing_temporizador.html',
        sesiones=sesiones[:10],
        total_sesiones=len(sesiones),
        total_segundos=total_segundos,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/ingles/shadowing/calendario')
@login_required
def shadowing_calendario():
    hoy = date.today()

    todas_sesiones = ShadowingSesion.query.filter_by(idUser=current_user.idUser).all()

    anios_con_datos = {s.fecha.date().year for s in todas_sesiones}
    anios_con_datos.add(hoy.year)
    anios_disponibles = sorted(anios_con_datos, reverse=True)

    anio_param = request.args.get('year', type=int)
    anio_seleccionado = anio_param if anio_param in anios_disponibles else hoy.year

    if anio_seleccionado == hoy.year:
        inicio = hoy - timedelta(days=370)
        fin = hoy
    else:
        inicio = date(anio_seleccionado, 1, 1)
        fin = date(anio_seleccionado, 12, 31)

    segundos_por_dia = defaultdict(int)
    for s in todas_sesiones:
        d = s.fecha.date()
        if inicio <= d <= fin:
            segundos_por_dia[d] += s.duracionSegundos

    def nivel_actividad(minutos):
        if minutos == 0:
            return 0
        if minutos < 5:
            return 1
        if minutos < 15:
            return 2
        if minutos < 30:
            return 3
        return 4

    inicio_grid = inicio - timedelta(days=inicio.weekday())
    fin_grid = fin + timedelta(days=(6 - fin.weekday()))

    dias = []
    cursor = inicio_grid
    while cursor <= fin_grid:
        segundos = segundos_por_dia.get(cursor, 0)
        minutos = segundos // 60
        dias.append({
            'fecha': cursor.isoformat(),
            'label': cursor.strftime('%d/%m/%Y'),
            'minutos': minutos,
            'segundos': segundos,
            'nivel': nivel_actividad(minutos),
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

    total_segundos_rango = sum(segundos_por_dia.values())
    dias_activos = len(segundos_por_dia)

    # Racha calculada sobre TODO el historial, no solo el año que se está viendo
    todos_los_dias = sorted({s.fecha.date() for s in todas_sesiones})
    racha_maxima = racha_temp = 0
    for i, dia in enumerate(todos_los_dias):
        if i == 0 or (dia - todos_los_dias[i - 1]).days == 1:
            racha_temp += 1
            racha_maxima = max(racha_maxima, racha_temp)
        else:
            racha_temp = 1

    racha_actual = 0
    if todos_los_dias:
        ultimo_dia = todos_los_dias[-1]
        if (hoy - ultimo_dia).days <= 1:
            dias_set = set(todos_los_dias)
            cursor2 = ultimo_dia
            while cursor2 in dias_set:
                racha_actual += 1
                cursor2 -= timedelta(days=1)

    letras_flotantes = get_letras_flotantes(current_user.idUser)

    return render_template(
        'menu/shadowing_calendario.html',
        semanas=semanas,
        total_minutos_rango=total_segundos_rango // 60,
        dias_activos=dias_activos,
        anios_disponibles=anios_disponibles,
        anio_seleccionado=anio_seleccionado,
        racha_actual=racha_actual,
        racha_maxima=racha_maxima,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/ingles/shadowing/guardar', methods=['POST'])
@login_required
def shadowing_guardar():
    data = request.get_json(silent=True) or {}
    segundos = data.get('segundos')

    if not isinstance(segundos, int) or segundos <= 0:
        return jsonify({'success': False}), 400

    sesion = ShadowingSesion(idUser=current_user.idUser, duracionSegundos=segundos)
    db.session.add(sesion)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/ingles/shadowing/registro')
@login_required
def shadowing_registro():
    query = ShadowingSesion.query.filter_by(idUser=current_user.idUser).order_by(ShadowingSesion.fecha.desc())
    total = query.count()

    POR_PAGINA = 7
    total_paginas = max(1, ceil(total / POR_PAGINA))
    pagina = request.args.get('page', 1, type=int)
    pagina = min(max(pagina, 1), total_paginas)
    sesiones = query.offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template(
        'menu/shadowing_registro.html',
        sesiones=sesiones,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/ingles/shadowing/<int:sesion_id>/editar', methods=['POST'])
@login_required
def shadowing_editar(sesion_id):
    sesion = ShadowingSesion.query.filter_by(idSesion=sesion_id, idUser=current_user.idUser).first_or_404()
    minutos = request.form.get('minutos', type=int) or 0
    segundos = request.form.get('segundos', type=int) or 0
    total_segundos = (minutos * 60) + segundos

    if total_segundos <= 0:
        flash("La duración debe ser mayor a 0.", "warning")
    else:
        sesion.duracionSegundos = total_segundos
        db.session.commit()
        flash("Sesión actualizada correctamente.", "success")

    return redirect(url_for('menu.shadowing_registro'))

@bp.route('/ingles/shadowing/<int:sesion_id>/eliminar', methods=['POST'])
@login_required
def shadowing_eliminar(sesion_id):
    sesion = ShadowingSesion.query.filter_by(idSesion=sesion_id, idUser=current_user.idUser).first_or_404()
    db.session.delete(sesion)
    db.session.commit()
    flash("Sesión eliminada de tu registro.", "success")
    return redirect(url_for('menu.shadowing_registro'))

@bp.route('/ingles/vocabulario', methods=['GET', 'POST'])
@login_required
def vocabulario():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        significado = request.form.get('significado')
        ejemplos = request.form.get('ejemplos')

        ya_existe = Vocabulario.query.filter(
            Vocabulario.idUser == current_user.idUser,
            db.func.lower(Vocabulario.nombre) == nombre.lower()
        ).first()

        if ya_existe:
            flash(f"La palabra '{nombre}' ya está en tu vocabulario.", "warning")
        else:
            nueva_palabra = Vocabulario(
                idUser=current_user.idUser,
                nombre=nombre,
                significado=significado,
                ejemplos=ejemplos
            )
            db.session.add(nueva_palabra)
            db.session.commit()
            flash(f"Palabra '{nombre}' agregada a tu vocabulario.", "success")

        return redirect(url_for('menu.vocabulario'))

    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template('menu/vocabulario.html', letras_flotantes=letras_flotantes)

@bp.route('/ingles/vocabulario/lista')
@login_required
def vocabulario_lista():
    busqueda = request.args.get('q', '', type=str).strip()

    query = Vocabulario.query.filter_by(idUser=current_user.idUser)
    if busqueda:
        like = f'%{busqueda}%'
        query = query.filter(
            db.or_(Vocabulario.nombre.ilike(like), Vocabulario.significado.ilike(like))
        )
    query = query.order_by(Vocabulario.createdAt.desc())

    total = query.count()
    POR_PAGINA = 10
    total_paginas = max(1, ceil(total / POR_PAGINA))
    pagina = request.args.get('page', 1, type=int)
    pagina = min(max(pagina, 1), total_paginas)
    palabras = query.offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    # Cuántas veces ha aparecido cada palabra al practicar en "Aprender Vocabulario"
    conteo_por_palabra = defaultdict(int)
    for r in VocabularioRegistro.query.filter_by(idUser=current_user.idUser).all():
        if r.idVocab is not None:
            conteo_por_palabra[r.idVocab] += 1

    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template(
        'menu/vocabulario_lista.html',
        palabras=palabras,
        conteo_por_palabra=conteo_por_palabra,
        letras_flotantes=letras_flotantes,
        busqueda=busqueda,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
    )

@bp.route('/ingles/vocabulario/calendario')
@login_required
def vocabulario_calendario():
    hoy = date.today()

    todos_registros = VocabularioRegistro.query.filter_by(idUser=current_user.idUser).all()

    anios_con_datos = {r.fecha.date().year for r in todos_registros}
    anios_con_datos.add(hoy.year)
    anios_disponibles = sorted(anios_con_datos, reverse=True)

    anio_param = request.args.get('year', type=int)
    anio_seleccionado = anio_param if anio_param in anios_disponibles else hoy.year

    if anio_seleccionado == hoy.year:
        inicio = hoy - timedelta(days=370)
        fin = hoy
    else:
        inicio = date(anio_seleccionado, 1, 1)
        fin = date(anio_seleccionado, 12, 31)

    conteo = defaultdict(int)
    palabras_por_dia = defaultdict(list)
    for r in todos_registros:
        d = r.fecha.date()
        if inicio <= d <= fin:
            conteo[d] += 1
            palabras_por_dia[d].append(r.palabraNombre)

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
            'palabras': palabras_por_dia.get(cursor, []),
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

    total_practicas = sum(conteo.values())
    dias_activos = len(conteo)

    # Racha calculada sobre TODO el historial, no solo el año que se está viendo
    todos_los_dias = sorted({r.fecha.date() for r in todos_registros})
    racha_maxima = racha_temp = 0
    for i, dia in enumerate(todos_los_dias):
        if i == 0 or (dia - todos_los_dias[i - 1]).days == 1:
            racha_temp += 1
            racha_maxima = max(racha_maxima, racha_temp)
        else:
            racha_temp = 1

    racha_actual = 0
    if todos_los_dias:
        ultimo_dia = todos_los_dias[-1]
        if (hoy - ultimo_dia).days <= 1:
            dias_set = set(todos_los_dias)
            cursor2 = ultimo_dia
            while cursor2 in dias_set:
                racha_actual += 1
                cursor2 -= timedelta(days=1)

    letras_flotantes = get_letras_flotantes(current_user.idUser)

    return render_template(
        'menu/vocabulario_calendario.html',
        semanas=semanas,
        total_practicas=total_practicas,
        dias_activos=dias_activos,
        anios_disponibles=anios_disponibles,
        anio_seleccionado=anio_seleccionado,
        racha_actual=racha_actual,
        racha_maxima=racha_maxima,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/ingles/vocabulario/<int:vocab_id>/editar', methods=['POST'])
@login_required
def vocabulario_editar(vocab_id):
    palabra = Vocabulario.query.filter_by(idVocab=vocab_id, idUser=current_user.idUser).first_or_404()
    palabra.nombre = request.form.get('nombre', palabra.nombre)
    palabra.significado = request.form.get('significado', palabra.significado)
    palabra.ejemplos = request.form.get('ejemplos', palabra.ejemplos)
    db.session.commit()
    flash(f"Palabra '{palabra.nombre}' actualizada correctamente.", "success")
    return redirect(url_for('menu.vocabulario_lista'))

@bp.route('/ingles/vocabulario/<int:vocab_id>/eliminar', methods=['POST'])
@login_required
def vocabulario_eliminar(vocab_id):
    palabra = Vocabulario.query.filter_by(idVocab=vocab_id, idUser=current_user.idUser).first_or_404()
    nombre = palabra.nombre
    db.session.delete(palabra)
    db.session.commit()
    flash(f"Palabra '{nombre}' eliminada de tu vocabulario.", "success")
    return redirect(url_for('menu.vocabulario_lista'))

@bp.route('/ingles/vocabulario/aprender')
@login_required
def vocabulario_aprender():
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    palabras = Vocabulario.query.filter_by(idUser=current_user.idUser).order_by(Vocabulario.createdAt.desc()).all()

    # Última calificación y cuántas veces ha aparecido cada palabra (para armar rondas
    # donde ninguna palabra se repite hasta que todas hayan salido la misma cantidad de veces)
    registros_usuario = VocabularioRegistro.query.filter_by(idUser=current_user.idUser).order_by(VocabularioRegistro.fecha.desc()).all()
    conteo_por_palabra = defaultdict(int)
    ultima_calificacion_por_palabra = {}
    for r in registros_usuario:
        if r.idVocab is None:
            continue
        conteo_por_palabra[r.idVocab] += 1
        if r.idVocab not in ultima_calificacion_por_palabra:
            ultima_calificacion_por_palabra[r.idVocab] = r.calificacion

    # Peso para que las palabras marcadas como más difíciles tengan más probabilidad de salir
    peso_por_calificacion = {'dificil': 3, 'medio': 2, 'facil': 1}
    palabras_data = []
    for p in palabras:
        calificacion = ultima_calificacion_por_palabra.get(p.idVocab)
        peso = peso_por_calificacion.get(calificacion, 2) if calificacion else 2

        item = p.to_dict()
        item['peso'] = peso
        item['vecesMostrada'] = conteo_por_palabra.get(p.idVocab, 0)
        palabras_data.append(item)

    return render_template('menu/vocabulario_aprender.html', palabras=palabras, palabras_data=palabras_data, letras_flotantes=letras_flotantes)

# Rangos por cantidad de palabras agregadas, escalados hacia una meta real de 3,650 palabras
RANGOS_VOCABULARIO = [
    {'nombre': 'Novato', 'emoji': '🐣', 'umbral': 0},
    {'nombre': 'Aprendiz', 'emoji': '📖', 'umbral': 25},
    {'nombre': 'Explorador', 'emoji': '🧭', 'umbral': 75},
    {'nombre': 'Constante', 'emoji': '🔥', 'umbral': 150},
    {'nombre': 'Avanzado', 'emoji': '🚀', 'umbral': 300},
    {'nombre': 'Experto', 'emoji': '🎓', 'umbral': 600},
    {'nombre': 'Maestro', 'emoji': '🏆', 'umbral': 1000},
    {'nombre': 'Virtuoso', 'emoji': '💎', 'umbral': 1825},
    {'nombre': 'Políglota', 'emoji': '👑', 'umbral': 3650},
]

# Rangos por porcentaje de palabras dominadas (calificadas como "Fácil").
# Umbrales altos a propósito: este rango debe costar trabajo, no regalarse.
RANGOS_DOMINIO = [
    {'nombre': 'Principiante', 'emoji': '🌱', 'umbral': 0},
    {'nombre': 'En Progreso', 'emoji': '⚡', 'umbral': 35},
    {'nombre': 'Competente', 'emoji': '🎯', 'umbral': 60},
    {'nombre': 'Fluido', 'emoji': '🌟', 'umbral': 85},
    {'nombre': 'Dominado', 'emoji': '💯', 'umbral': 98},
]

# Palabras distintas que debes tener calificadas antes de que el % de dominio cuente de verdad
MINIMO_CALIFICACIONES_DOMINIO = 10

def calcular_rango(valor, tiers):
    rango_actual = tiers[0]
    siguiente = None
    for i, r in enumerate(tiers):
        if valor >= r['umbral']:
            rango_actual = r
            siguiente = tiers[i + 1] if i + 1 < len(tiers) else None

    if siguiente:
        base = rango_actual['umbral']
        meta = siguiente['umbral']
        pct_progreso = round(((valor - base) / (meta - base)) * 100)
        faltan = round(meta - valor, 1)
    else:
        pct_progreso = 100
        faltan = 0

    return rango_actual, siguiente, pct_progreso, faltan

@bp.route('/ingles/vocabulario/rango')
@login_required
def vocabulario_rango():
    total_palabras = Vocabulario.query.filter_by(idUser=current_user.idUser).count()
    rango_actual, siguiente_rango, pct_progreso, faltan = calcular_rango(total_palabras, RANGOS_VOCABULARIO)

    # Solo cuenta la calificación más reciente de cada palabra: repetir "Fácil"
    # en la misma palabra una y otra vez ya no infla el porcentaje.
    registros = VocabularioRegistro.query.filter_by(idUser=current_user.idUser).order_by(VocabularioRegistro.fecha.asc()).all()
    ultima_calificacion_por_palabra = {}
    for r in registros:
        clave = r.idVocab if r.idVocab is not None else r.palabraNombre
        ultima_calificacion_por_palabra[clave] = r.calificacion

    total_facil = sum(1 for c in ultima_calificacion_por_palabra.values() if c == 'facil')
    total_medio = sum(1 for c in ultima_calificacion_por_palabra.values() if c == 'medio')
    total_dificil = sum(1 for c in ultima_calificacion_por_palabra.values() if c == 'dificil')
    total_calificaciones = len(ultima_calificacion_por_palabra)

    if total_calificaciones < MINIMO_CALIFICACIONES_DOMINIO:
        # Aún no hay suficientes palabras calificadas para que el rango de dominio sea confiable
        pct_dominio = round((total_facil / total_calificaciones * 100) if total_calificaciones > 0 else 0, 1)
        rango_dominio = RANGOS_DOMINIO[0]
        siguiente_dominio = RANGOS_DOMINIO[1]
        pct_progreso_dominio = round((total_calificaciones / MINIMO_CALIFICACIONES_DOMINIO) * 100)
        faltan_dominio = None
        faltan_calificaciones = MINIMO_CALIFICACIONES_DOMINIO - total_calificaciones
    else:
        pct_dominio = round((total_facil / total_calificaciones * 100), 1)
        rango_dominio, siguiente_dominio, pct_progreso_dominio, faltan_dominio = calcular_rango(pct_dominio, RANGOS_DOMINIO)
        faltan_calificaciones = 0

    letras_flotantes = get_letras_flotantes(current_user.idUser)

    return render_template(
        'menu/vocabulario_rango.html',
        total_palabras=total_palabras,
        rango_actual=rango_actual,
        siguiente_rango=siguiente_rango,
        pct_progreso=pct_progreso,
        faltan=faltan,
        rangos=RANGOS_VOCABULARIO,
        total_facil=total_facil,
        total_medio=total_medio,
        total_dificil=total_dificil,
        minimo_calificaciones_dominio=MINIMO_CALIFICACIONES_DOMINIO,
        faltan_calificaciones=faltan_calificaciones,
        total_calificaciones=total_calificaciones,
        pct_dominio=pct_dominio,
        rango_dominio=rango_dominio,
        siguiente_dominio=siguiente_dominio,
        pct_progreso_dominio=pct_progreso_dominio,
        faltan_dominio=faltan_dominio,
        rangos_dominio=RANGOS_DOMINIO,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/ingles/vocabulario/calificar', methods=['POST'])
@login_required
def vocabulario_calificar():
    data = request.get_json(silent=True) or {}
    id_vocab = data.get('idVocab')
    nombre = data.get('nombre')
    calificacion = data.get('calificacion')

    if calificacion not in ('facil', 'medio', 'dificil') or not nombre:
        return jsonify({'success': False}), 400

    registro = VocabularioRegistro(
        idUser=current_user.idUser,
        idVocab=id_vocab,
        palabraNombre=nombre,
        calificacion=calificacion
    )
    db.session.add(registro)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/ingles/vocabulario/historial')
@login_required
def vocabulario_historial():
    registros = VocabularioRegistro.query.filter_by(idUser=current_user.idUser).order_by(VocabularioRegistro.fecha.desc()).all()

    total_facil = sum(1 for r in registros if r.calificacion == 'facil')
    total_medio = sum(1 for r in registros if r.calificacion == 'medio')
    total_dificil = sum(1 for r in registros if r.calificacion == 'dificil')
    total = len(registros)

    def pct(n):
        return round((n / total * 100) if total > 0 else 0)

    # Paginación de la tabla: 15 registros por página
    POR_PAGINA = 15
    total_paginas = max(1, ceil(total / POR_PAGINA))
    pagina = request.args.get('page', 1, type=int)
    pagina = min(max(pagina, 1), total_paginas)
    inicio = (pagina - 1) * POR_PAGINA
    registros_pagina = registros[inicio:inicio + POR_PAGINA]

    letras_flotantes = get_letras_flotantes(current_user.idUser)

    return render_template(
        'menu/vocabulario_historial.html',
        registros=registros_pagina,
        total_facil=total_facil,
        total_medio=total_medio,
        total_dificil=total_dificil,
        total=total,
        pct_facil=pct(total_facil),
        pct_medio=pct(total_medio),
        pct_dificil=pct(total_dificil),
        pagina=pagina,
        total_paginas=total_paginas,
        letras_flotantes=letras_flotantes,
    )
