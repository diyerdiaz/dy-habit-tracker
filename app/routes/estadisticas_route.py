from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models.estadisticas import (
    leer_mes, meses_disponibles, estadisticas_del_mes, nombre_mes,
    leer_meses, comparar_meses, calendario_del_mes, MAX_MESES_COMPARAR,
)

bp = Blueprint('estadisticas', __name__, url_prefix='/estadisticas')


def _navegacion_mes(anio, mes, hoy):
    """Datos para el selector de mes con flechas (anterior / siguiente)."""
    meses = meses_disponibles(current_user.idUser, hoy)
    valores = [m['valor'] for m in meses]
    actual = f"{anio}-{mes:02d}"
    if actual not in valores:
        valores.insert(0, actual)
    posicion = valores.index(actual)
    return {
        'mes_actual': actual,
        'mes_nombre': nombre_mes(anio, mes),
        'meses': meses,
        # La lista va del más reciente al más antiguo
        'mes_anterior': valores[posicion + 1] if posicion + 1 < len(valores) else None,
        'mes_siguiente': valores[posicion - 1] if posicion > 0 else None,
        'es_mes_en_curso': (anio, mes) == (hoy.year, hoy.month),
    }


@bp.route('/')
@login_required
def index():
    hoy = date.today()
    anio, mes = leer_mes(request.args.get('mes'), hoy)
    return render_template(
        'estadisticas/index.html',
        pestana='resumen',
        stats=estadisticas_del_mes(current_user.idUser, anio, mes, hoy),
        **_navegacion_mes(anio, mes, hoy),
    )


@bp.route('/comparar')
@login_required
def comparar():
    hoy = date.today()
    elegidos = leer_meses(request.args.getlist('m'), hoy)
    return render_template(
        'estadisticas/comparar.html',
        pestana='comparar',
        comparacion=comparar_meses(current_user.idUser, elegidos, hoy),
        meses=meses_disponibles(current_user.idUser, hoy),
        elegidos={f"{a}-{m:02d}" for a, m in elegidos},
        max_meses=MAX_MESES_COMPARAR,
    )


@bp.route('/calendario')
@login_required
def calendario():
    hoy = date.today()
    anio, mes = leer_mes(request.args.get('mes'), hoy)
    return render_template(
        'estadisticas/calendario.html',
        pestana='calendario',
        cal=calendario_del_mes(current_user.idUser, anio, mes, hoy),
        **_navegacion_mes(anio, mes, hoy),
    )
