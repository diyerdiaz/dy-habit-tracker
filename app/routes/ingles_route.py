from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.shadowing_sesion import ShadowingSesion
from app import db
from app.services.ingles import get_letras_flotantes, resumen_ingles, graficas_ingles
from app.services.palabras_aleatorias import (
    palabras_aleatorias as elegir_palabras_aleatorias, normalizar_cantidad, total_vocabulario,
    MINIMO_PALABRAS, MAXIMO_PALABRAS, CANTIDAD_POR_DEFECTO,
)
from collections import defaultdict
from datetime import date, timedelta
from math import ceil

bp = Blueprint('ingles', __name__, url_prefix='/menu/ingles')

@bp.route('')
@login_required
def ingles():
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template('ingles/index.html', letras_flotantes=letras_flotantes,
                           resumen=resumen_ingles(current_user.idUser),
                           graficas=graficas_ingles(current_user.idUser))

@bp.route('/palabras-aleatorias')
@login_required
def palabras_aleatorias():
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    cantidad = normalizar_cantidad(request.args.get('cantidad'))
    palabras = elegir_palabras_aleatorias(current_user.idUser, cantidad) if cantidad else []
    return render_template(
        'ingles/palabras_aleatorias.html',
        palabras=palabras,
        pedidas=cantidad,
        total_vocabulario=total_vocabulario(current_user.idUser),
        cantidad=cantidad or CANTIDAD_POR_DEFECTO,
        minimo=MINIMO_PALABRAS,
        maximo=MAXIMO_PALABRAS,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/pronunciacion')
@login_required
def pronunciacion():
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template('ingles/pronunciacion.html', letras_flotantes=letras_flotantes)

@bp.route('/shadowing')
@login_required
def shadowing():
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template('ingles/shadowing.html', letras_flotantes=letras_flotantes)

@bp.route('/shadowing/temporizador')
@login_required
def shadowing_temporizador():
    sesiones = ShadowingSesion.query.filter_by(idUser=current_user.idUser).all()
    total_segundos = sum(s.duracionSegundos for s in sesiones)
    letras_flotantes = get_letras_flotantes(current_user.idUser)
    return render_template(
        'ingles/shadowing_temporizador.html',
        total_sesiones=len(sesiones),
        total_segundos=total_segundos,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/shadowing/calendario')
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
        'ingles/shadowing_calendario.html',
        semanas=semanas,
        total_minutos_rango=total_segundos_rango // 60,
        dias_activos=dias_activos,
        anios_disponibles=anios_disponibles,
        anio_seleccionado=anio_seleccionado,
        racha_actual=racha_actual,
        racha_maxima=racha_maxima,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/shadowing/guardar', methods=['POST'])
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

@bp.route('/shadowing/registro')
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
        'ingles/shadowing_registro.html',
        sesiones=sesiones,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/shadowing/<int:sesion_id>/editar', methods=['POST'])
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

    return redirect(url_for('ingles.shadowing_registro'))

@bp.route('/shadowing/<int:sesion_id>/eliminar', methods=['POST'])
@login_required
def shadowing_eliminar(sesion_id):
    sesion = ShadowingSesion.query.filter_by(idSesion=sesion_id, idUser=current_user.idUser).first_or_404()
    db.session.delete(sesion)
    db.session.commit()
    flash("Sesión eliminada de tu registro.", "success")
    return redirect(url_for('ingles.shadowing_registro'))
