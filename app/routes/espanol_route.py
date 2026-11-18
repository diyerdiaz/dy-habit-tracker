from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('espanol', __name__, url_prefix='/menu/espanol')

# Lo que tendrá la sección; por ahora se muestran como "próximamente"
SECCIONES_PROXIMAS = [
    {'icono': 'bi-journal-text', 'nombre': 'Vocabulario'},
    {'icono': 'bi-spellcheck', 'nombre': 'Ortografía'},
    {'icono': 'bi-book-half', 'nombre': 'Lectura'},
    {'icono': 'bi-pencil-square', 'nombre': 'Escritura'},
]


@bp.route('')
@login_required
def index():
    return render_template('espanol/index.html', secciones=SECCIONES_PROXIMAS)
