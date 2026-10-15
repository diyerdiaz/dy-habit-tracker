from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models.estadisticas import leer_mes, meses_disponibles, estadisticas_del_mes, nombre_mes

bp = Blueprint('estadisticas', __name__, url_prefix='/estadisticas')


@bp.route('/')
@login_required
def index():
    hoy = date.today()
    anio, mes = leer_mes(request.args.get('mes'), hoy)
    meses = meses_disponibles(current_user.idUser, hoy)
    valores = [m['valor'] for m in meses]
    actual = f"{anio}-{mes:02d}"
    if actual not in valores:
        valores.insert(0, actual)
    posicion = valores.index(actual)

    return render_template(
        'estadisticas/index.html',
        stats=estadisticas_del_mes(current_user.idUser, anio, mes, hoy),
        mes_actual=actual,
        mes_nombre=nombre_mes(anio, mes),
        meses=meses,
        # La lista va del más reciente al más antiguo
        mes_anterior=valores[posicion + 1] if posicion + 1 < len(valores) else None,
        mes_siguiente=valores[posicion - 1] if posicion > 0 else None,
        es_mes_en_curso=(anio, mes) == (hoy.year, hoy.month),
    )
