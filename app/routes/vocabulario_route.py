"""Vocabulario: agregar palabras, lista, calendario, rango, historial y
"Aprender Vocabulario" (tarjetas por rondas).

El mismo blueprint se registra dos veces (ver app/__init__.py):
  - 'vocabulario'    en /menu/ingles/vocabulario   (palabras en inglés)
  - 'vocabulario_es' en /menu/espanol/vocabulario  (palabras en español)
Cada vista usa idioma_actual() para ver y guardar solo las palabras de su sección,
y las plantillas usan `sec` (services/secciones.py) para los textos y enlaces."""
from collections import defaultdict
from datetime import date, timedelta
from math import ceil

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app import db
from app.models.vocabulario import Vocabulario
from app.models.vocabulario_registro import VocabularioRegistro
from app.services import diccionario
from app.services.ingles import (
    get_letras_flotantes, calcular_rango,
    rangos_vocabulario, rangos_dominio, MINIMO_CALIFICACIONES_DOMINIO,
    TIEMPOS_TARJETA, TIEMPO_TARJETA_POR_DEFECTO,
)
from app.services.secciones import idioma_actual, seccion_actual

bp = Blueprint('vocabulario', __name__, url_prefix='/menu/ingles/vocabulario')


@bp.route('', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        significado = request.form.get('significado')
        ejemplos = request.form.get('ejemplos')

        ya_existe = Vocabulario.query.filter(
            Vocabulario.idUser == current_user.idUser,
            Vocabulario.idioma == idioma_actual(),
            db.func.lower(Vocabulario.nombre) == nombre.lower()
        ).first()

        if ya_existe:
            flash(f"La palabra '{nombre}' ya está en tu vocabulario.", "warning")
        else:
            nueva_palabra = Vocabulario(
                idUser=current_user.idUser,
                idioma=idioma_actual(),
                nombre=nombre,
                significado=significado,
                ejemplos=ejemplos
            )
            db.session.add(nueva_palabra)
            db.session.commit()
            flash(f"Palabra '{nombre}' agregada a tu vocabulario.", "success")

        return redirect(url_for(f'{request.blueprint}.index'))

    letras_flotantes = get_letras_flotantes(current_user.idUser, idioma_actual())
    return render_template('vocabulario/index.html', letras_flotantes=letras_flotantes)


@bp.route('/autocompletar', methods=['POST'])
@login_required
def autocompletar():
    """Significados en español y una frase de ejemplo para la palabra en inglés
    que se escribió (MyMemory + Tatoeba, gratis y sin clave)."""
    if not seccion_actual()['autocompletar']:
        abort(404)   # solo existe para palabras en inglés
    data = request.get_json(silent=True) or {}
    palabra = diccionario.limpiar_palabra(data.get('palabra'))
    if not palabra:
        return jsonify({'success': False,
                        'error': 'Escribe una palabra o expresión en inglés (solo letras).'}), 400
    if not diccionario.registrar_uso(current_user.idUser):
        return jsonify({'success': False,
                        'error': 'Llegaste al límite de autocompletados de hoy. Mañana puedes seguir.'}), 429
    try:
        resultado = diccionario.autocompletar(palabra)
    except diccionario.ErrorDiccionario as e:
        return jsonify({'success': False, 'error': str(e)}), 502
    return jsonify({'success': True, **resultado})

@bp.route('/lista')
@login_required
def lista():
    busqueda = request.args.get('q', '', type=str).strip()

    query = Vocabulario.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual())
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
    for r in VocabularioRegistro.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual()).all():
        if r.idVocab is not None:
            conteo_por_palabra[r.idVocab] += 1

    letras_flotantes = get_letras_flotantes(current_user.idUser, idioma_actual())
    return render_template(
        'vocabulario/lista.html',
        palabras=palabras,
        conteo_por_palabra=conteo_por_palabra,
        letras_flotantes=letras_flotantes,
        busqueda=busqueda,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
    )

@bp.route('/calendario')
@login_required
def calendario():
    hoy = date.today()

    todos_registros = VocabularioRegistro.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual()).all()

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

    letras_flotantes = get_letras_flotantes(current_user.idUser, idioma_actual())

    return render_template(
        'vocabulario/calendario.html',
        semanas=semanas,
        total_practicas=total_practicas,
        dias_activos=dias_activos,
        anios_disponibles=anios_disponibles,
        anio_seleccionado=anio_seleccionado,
        racha_actual=racha_actual,
        racha_maxima=racha_maxima,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/<int:vocab_id>/editar', methods=['POST'])
@login_required
def editar(vocab_id):
    palabra = Vocabulario.query.filter_by(idVocab=vocab_id, idUser=current_user.idUser, idioma=idioma_actual()).first_or_404()
    palabra.nombre = request.form.get('nombre', palabra.nombre)
    palabra.significado = request.form.get('significado', palabra.significado)
    palabra.ejemplos = request.form.get('ejemplos', palabra.ejemplos)
    db.session.commit()
    flash(f"Palabra '{palabra.nombre}' actualizada correctamente.", "success")
    return redirect(url_for(f'{request.blueprint}.lista'))

@bp.route('/<int:vocab_id>/eliminar', methods=['POST'])
@login_required
def eliminar(vocab_id):
    palabra = Vocabulario.query.filter_by(idVocab=vocab_id, idUser=current_user.idUser, idioma=idioma_actual()).first_or_404()
    nombre = palabra.nombre
    db.session.delete(palabra)
    db.session.commit()
    flash(f"Palabra '{nombre}' eliminada de tu vocabulario.", "success")
    return redirect(url_for(f'{request.blueprint}.lista'))

@bp.route('/aprender')
@login_required
def aprender():
    letras_flotantes = get_letras_flotantes(current_user.idUser, idioma_actual())
    palabras = Vocabulario.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual()).order_by(Vocabulario.createdAt.desc()).all()

    # Última calificación y cuántas veces ha aparecido cada palabra: las marcadas
    # "Difícil" van primero en la siguiente ronda y el resto va por turnos (ninguna
    # se repite hasta que todas hayan salido la misma cantidad de veces)
    registros_usuario = VocabularioRegistro.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual()).order_by(VocabularioRegistro.fecha.desc()).all()
    conteo_por_palabra = defaultdict(int)
    ultima_calificacion_por_palabra = {}
    # Las palabras ya practicadas hoy no vuelven a salir hasta mañana
    hoy = date.today()
    estudiadas_hoy = set()
    for r in registros_usuario:
        if r.idVocab is None:
            continue
        conteo_por_palabra[r.idVocab] += 1
        if r.fecha and r.fecha.date() == hoy:
            estudiadas_hoy.add(r.idVocab)
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
        # Las que quedaron en "Difícil" salen primero en la siguiente ronda
        item['ultimaCalificacion'] = calificacion
        item['estudiadaHoy'] = p.idVocab in estudiadas_hoy
        palabras_data.append(item)

    pendientes_hoy = sum(1 for p in palabras_data if not p['estudiadaHoy'])
    return render_template('vocabulario/aprender.html', palabras=palabras, palabras_data=palabras_data,
                           pendientes_hoy=pendientes_hoy,
                           letras_flotantes=letras_flotantes, tiempos_tarjeta=TIEMPOS_TARJETA,
                           tiempo_por_defecto=TIEMPO_TARJETA_POR_DEFECTO)


@bp.route('/rango')
@login_required
def rango():
    # Cada idioma con su escalera de rangos (Español tiene nombres propios)
    escalera = rangos_vocabulario(idioma_actual())
    escalera_dominio = rangos_dominio(idioma_actual())
    total_palabras = Vocabulario.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual()).count()
    rango_actual, siguiente_rango, pct_progreso, faltan = calcular_rango(total_palabras, escalera)

    # Solo cuenta la calificación más reciente de cada palabra: repetir "Fácil"
    # en la misma palabra una y otra vez ya no infla el porcentaje.
    registros = VocabularioRegistro.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual()).order_by(VocabularioRegistro.fecha.asc()).all()
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
        rango_dominio = escalera_dominio[0]
        siguiente_dominio = escalera_dominio[1]
        pct_progreso_dominio = round((total_calificaciones / MINIMO_CALIFICACIONES_DOMINIO) * 100)
        faltan_dominio = None
        faltan_calificaciones = MINIMO_CALIFICACIONES_DOMINIO - total_calificaciones
    else:
        pct_dominio = round((total_facil / total_calificaciones * 100), 1)
        rango_dominio, siguiente_dominio, pct_progreso_dominio, faltan_dominio = calcular_rango(pct_dominio, escalera_dominio)
        faltan_calificaciones = 0

    letras_flotantes = get_letras_flotantes(current_user.idUser, idioma_actual())

    return render_template(
        'vocabulario/rango.html',
        total_palabras=total_palabras,
        rango_actual=rango_actual,
        siguiente_rango=siguiente_rango,
        pct_progreso=pct_progreso,
        faltan=faltan,
        rangos=escalera,
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
        rangos_dominio=escalera_dominio,
        letras_flotantes=letras_flotantes,
    )

@bp.route('/calificar', methods=['POST'])
@login_required
def calificar():
    data = request.get_json(silent=True) or {}
    id_vocab = data.get('idVocab')
    nombre = data.get('nombre')
    calificacion = data.get('calificacion')

    if calificacion not in ('facil', 'medio', 'dificil') or not nombre:
        return jsonify({'success': False}), 400

    registro = VocabularioRegistro(
        idUser=current_user.idUser,
        idioma=idioma_actual(),
        idVocab=id_vocab,
        palabraNombre=nombre,
        calificacion=calificacion
    )
    db.session.add(registro)
    db.session.commit()
    return jsonify({'success': True, 'idRegistro': registro.idRegistro})


@bp.route('/calificar/<int:id_registro>/corregir', methods=['POST'])
@login_required
def corregir(id_registro):
    """Cambia la calificación de una tarjeta ya calificada (se le dio al botón
    equivocado): se corrige el mismo registro, no se suma una vista más."""
    data = request.get_json(silent=True) or {}
    calificacion = data.get('calificacion')
    if calificacion not in ('facil', 'medio', 'dificil'):
        return jsonify({'success': False}), 400

    registro = VocabularioRegistro.query.filter_by(
        idRegistro=id_registro, idUser=current_user.idUser, idioma=idioma_actual()
    ).first_or_404()
    registro.calificacion = calificacion
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/historial')
@login_required
def historial():
    registros = VocabularioRegistro.query.filter_by(idUser=current_user.idUser, idioma=idioma_actual()).order_by(VocabularioRegistro.fecha.desc()).all()

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

    letras_flotantes = get_letras_flotantes(current_user.idUser, idioma_actual())

    return render_template(
        'vocabulario/historial.html',
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
