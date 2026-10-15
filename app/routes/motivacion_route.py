from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required
from app.models.motivacion import frase_del_dia, reto_del_dia, frases_anteriores
from app.models.habitos import DIAS_SEMANA

bp = Blueprint('motivacion', __name__, url_prefix='/motivacion')

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _fecha_texto(fecha):
    return f"{DIAS_SEMANA[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


@bp.route('/')
@login_required
def index():
    hoy = date.today()
    anteriores = [{**f, 'fecha_texto': _fecha_texto(f['fecha'])} for f in frases_anteriores()]
    return render_template(
        'motivacion/index.html',
        frase=frase_del_dia(hoy),
        reto=reto_del_dia(hoy),
        fecha_texto=_fecha_texto(hoy),
        anteriores=anteriores,
    )
