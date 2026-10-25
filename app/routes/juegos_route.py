"""Juegos de vocabulario de la sección Inglés.

Unir parejas: palabras en inglés a la izquierda y significados a la derecha.
Sopa de letras: los significados son las pistas y hay que encontrar la palabra
en inglés dentro de la cuadrícula.
El navegador recibe todas las palabras al abrir la página y arma las rondas solo,
así se puede jugar aunque el internet esté lento; al terminar cada ronda envía
el resultado para guardarlo en tus estadísticas.
"""
import re
import unicodedata
from collections import defaultdict
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.juego_partida import JuegoPartida, JUEGOS, NIVELES_SOPA
from app.models.vocabulario import Vocabulario
from app.routes.menu_route import get_letras_flotantes

bp = Blueprint('juegos', __name__, url_prefix='/menu/ingles/juegos')

MINIMO_PALABRAS = 4      # con menos no hay con qué confundirse
PAREJAS_POR_RONDA = 6
# Sopa de letras: solo palabras de una pieza que quepan en la cuadrícula
MINIMO_PALABRAS_SOPA = 5
LETRAS_SOPA = (3, 10)


def _palabras_para_jugar(idUser):
    """Todas las palabras del usuario; el orden al azar lo decide el navegador."""
    return [
        {'id': p.idVocab, 'en': p.nombre.strip(), 'es': p.significado.strip()}
        for p in Vocabulario.query.filter_by(idUser=idUser).all()
        if p.nombre and p.nombre.strip() and p.significado and p.significado.strip()
    ]


def letras_para_sopa(palabra):
    """'Borrow' -> 'BORROW'. Devuelve None si no sirve para la sopa
    (espacios, guiones, apóstrofos, números o largo fuera de 3 a 10 letras)."""
    sin_tildes = unicodedata.normalize('NFD', palabra.strip()).encode('ascii', 'ignore').decode()
    letras = sin_tildes.upper()
    minimo, maximo = LETRAS_SOPA
    return letras if re.fullmatch(rf'[A-Z]{{{minimo},{maximo}}}', letras) else None


def _palabras_para_sopa(idUser):
    salida = []
    for p in _palabras_para_jugar(idUser):
        letras = letras_para_sopa(p['en'])
        if letras:
            salida.append({**p, 'letras': letras})
    return salida


def _resumen(idUser):
    partidas = JuegoPartida.query.filter_by(idUser=idUser).all()
    por_juego = defaultdict(list)
    for p in partidas:
        por_juego[p.juego].append(p)
    resumen = {}
    for clave, lista in por_juego.items():
        perfectas = [p for p in lista if p.errores == 0 and not p.pistas]
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
        total_sopa=len(_palabras_para_sopa(current_user.idUser)),
        minimo_sopa=MINIMO_PALABRAS_SOPA,
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


@bp.route('/sopa')
@login_required
def sopa():
    return render_template(
        'juegos/sopa.html',
        palabras=_palabras_para_sopa(current_user.idUser),
        total_palabras=len(_palabras_para_jugar(current_user.idUser)),
        minimo=MINIMO_PALABRAS_SOPA,
        por_ronda=PAREJAS_POR_RONDA,
        niveles=NIVELES_SOPA,
    )


@bp.route('/<juego>/resultado', methods=['POST'])
@login_required
def resultado(juego):
    """Guarda una ronda terminada. Recibe JSON: {"ids": [...], "errores": 2, "segundos": 41}
    y, en la sopa de letras, también "pistas" y "nivel"."""
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

    pistas, nivel = 0, None
    if juego == 'sopa':
        pistas, nivel = data.get('pistas', 0), data.get('nivel')
        if (not isinstance(pistas, int) or isinstance(pistas, bool) or not 0 <= pistas <= len(ids)
                or nivel not in NIVELES_SOPA):
            return jsonify({'success': False, 'error': 'Resultado no válido.'}), 400

    # Las palabras tienen que ser del usuario: no se puede inventar una ronda
    propias = Vocabulario.query.filter(
        Vocabulario.idUser == current_user.idUser, Vocabulario.idVocab.in_(ids)).count()
    if propias != len(ids):
        return jsonify({'success': False, 'error': 'Resultado no válido.'}), 400

    db.session.add(JuegoPartida(
        idUser=current_user.idUser, juego=juego, parejas=len(ids),
        errores=errores, segundos=segundos, nivel=nivel, pistas=pistas,
    ))
    db.session.commit()
    return jsonify({'success': True})
