"""Juegos de vocabulario de la sección Inglés.

Unir parejas: palabras en inglés a la izquierda y significados a la derecha.
El navegador recibe todas las palabras al abrir la página y arma las rondas solo,
así se puede jugar aunque el internet esté lento; al terminar cada ronda envía
el resultado para guardarlo en tus estadísticas.
"""
from collections import defaultdict
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.juego_partida import JuegoPartida, JUEGOS
from app.models.vocabulario import Vocabulario
from app.routes.menu_route import get_letras_flotantes

bp = Blueprint('juegos', __name__, url_prefix='/menu/ingles/juegos')

MINIMO_PALABRAS = 4      # con menos no hay con qué confundirse
PAREJAS_POR_RONDA = 6


def _palabras_para_jugar(idUser):
    """Todas las palabras del usuario; el orden al azar lo decide el navegador."""
    return [
        {'id': p.idVocab, 'en': p.nombre.strip(), 'es': p.significado.strip()}
        for p in Vocabulario.query.filter_by(idUser=idUser).all()
        if p.nombre and p.nombre.strip() and p.significado and p.significado.strip()
    ]


def _resumen(idUser):
    partidas = JuegoPartida.query.filter_by(idUser=idUser).all()
    por_juego = defaultdict(list)
    for p in partidas:
        por_juego[p.juego].append(p)
    resumen = {}
    for clave, lista in por_juego.items():
        perfectas = [p for p in lista if p.errores == 0]
        resumen[clave] = {
            'jugadas': len(lista),
            'precision': round(sum(p.precision for p in lista) / len(lista)),
            'mejor_tiempo': min((p.segundos for p in perfectas), default=None),
        }
    return resumen


@bp.route('/')
@login_required
def index():
    return render_template(
        'juegos/index.html',
        total_palabras=len(_palabras_para_jugar(current_user.idUser)),
        minimo=MINIMO_PALABRAS,
        resumen=_resumen(current_user.idUser),
        letras_flotantes=get_letras_flotantes(current_user.idUser),
    )


@bp.route('/unir')
@login_required
def unir():
    palabras = _palabras_para_jugar(current_user.idUser)
    return render_template(
        'juegos/unir.html',
        palabras=palabras,
        minimo=MINIMO_PALABRAS,
        parejas_por_ronda=PAREJAS_POR_RONDA,
    )


@bp.route('/<juego>/resultado', methods=['POST'])
@login_required
def resultado(juego):
    """Guarda una ronda terminada. Recibe JSON: {"ids": [...], "errores": 2, "segundos": 41}."""
    if juego not in JUEGOS:
        return jsonify({'success': False, 'error': 'Juego no válido.'}), 404
    data = request.get_json(silent=True) or {}
    ids = data.get('ids')
    errores, segundos = data.get('errores'), data.get('segundos')

    if (not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids)
            or len(set(ids)) != len(ids) or not MINIMO_PALABRAS <= len(ids) <= PAREJAS_POR_RONDA
            or not isinstance(errores, int) or not 0 <= errores <= 500
            or not isinstance(segundos, int) or not 0 <= segundos <= 3600):
        return jsonify({'success': False, 'error': 'Resultado no válido.'}), 400

    # Las palabras tienen que ser del usuario: no se puede inventar una ronda
    propias = Vocabulario.query.filter(
        Vocabulario.idUser == current_user.idUser, Vocabulario.idVocab.in_(ids)).count()
    if propias != len(ids):
        return jsonify({'success': False, 'error': 'Resultado no válido.'}), 400

    db.session.add(JuegoPartida(
        idUser=current_user.idUser, juego=juego, parejas=len(ids),
        errores=errores, segundos=segundos,
    ))
    db.session.commit()
    return jsonify({'success': True})
