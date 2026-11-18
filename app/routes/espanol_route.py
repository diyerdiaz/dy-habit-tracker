"""Sección Español: solo para practicar palabras. Tiene el mismo dashboard que
Inglés (sin shadowing); Vocabulario y Juegos son las mismas páginas que en
Inglés, registradas con otro nombre (vocabulario_es, juegos_es en app/__init__.py)."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.services.ingles import get_letras_flotantes, resumen_ingles, graficas_ingles
from app.services.secciones import ESPANOL

bp = Blueprint('espanol', __name__, url_prefix='/menu/espanol')


@bp.route('')
@login_required
def index():
    return render_template(
        'espanol/index.html',
        letras_flotantes=get_letras_flotantes(current_user.idUser, ESPANOL),
        resumen=resumen_ingles(current_user.idUser, idioma=ESPANOL),
        graficas=graficas_ingles(current_user.idUser, idioma=ESPANOL),
    )
