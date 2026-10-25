"""Juegos de vocabulario: Unir parejas."""
import json
import re
from app import db
from app.models.juego_partida import JuegoPartida
from app.models.user_progress import UserProgress
from app.models.vocabulario import Vocabulario

PALABRAS = [('give', 'dar'), ('take', 'tomar'), ('run', 'correr'), ('eat', 'comer'),
            ('sleep', 'dormir'), ('read', 'leer'), ('write', 'escribir')]


def _vocabulario(user, cuantas=len(PALABRAS)):
    for en, es in PALABRAS[:cuantas]:
        db.session.add(Vocabulario(idUser=user.idUser, nombre=en, significado=es))
    db.session.commit()
    return Vocabulario.query.filter_by(idUser=user.idUser).all()


def _palabras_de_la_pagina(html):
    bloque = re.search(r'<script type="application/json" id="unirPalabras">(.*?)</script>', html, re.S)
    return json.loads(bloque.group(1))


def _enviar(client, ids, errores=0, segundos=30):
    return client.post('/menu/ingles/juegos/unir/resultado', json={'ids': ids, 'errores': errores, 'segundos': segundos})


def _xp(user):
    progreso = db.session.get(UserProgress, user.idUser)
    return progreso.xpTotal if progreso else 0


# ── Páginas ──

def test_juegos_requiere_login(client):
    assert client.get('/menu/ingles/juegos/').status_code == 302
    assert client.get('/menu/ingles/juegos/unir').status_code == 302
    assert _enviar(client, [1, 2, 3, 4]).status_code in (302, 401)


def test_tarjeta_juegos_en_la_pagina_de_ingles(logged_client):
    html = logged_client.get('/menu/ingles').get_data(as_text=True)
    assert '/menu/ingles/juegos/' in html and 'Juegos' in html
    assert 'id="sidebar"' in html  # el menú lateral sigue apareciendo tras pasarlo a un partial


def test_sin_palabras_suficientes_pide_agregar(logged_client, user):
    _vocabulario(user, cuantas=3)
    html = logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True)
    assert 'Necesitas al menos' in html and 'id="juegoUnir"' not in html
    menu = logged_client.get('/menu/ingles/juegos/').get_data(as_text=True)
    assert 'bloqueado' in menu


def test_la_pagina_trae_las_palabras_del_usuario(logged_client, user, other_user):
    _vocabulario(user)
    db.session.add(Vocabulario(idUser=other_user.idUser, nombre='secret', significado='secreto'))
    db.session.commit()
    html = logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True)
    assert 'id="juegoUnir"' in html and 'js/juegos.js' in html and 'css/juegos.css' in html
    datos = _palabras_de_la_pagina(html)
    assert {p['en'] for p in datos} == {en for en, _ in PALABRAS}
    assert 'secret' not in html  # nunca las palabras de otra persona


def test_el_texto_de_las_palabras_va_escapado(logged_client, user):
    _vocabulario(user, cuantas=4)
    db.session.add(Vocabulario(idUser=user.idUser, nombre='</script><b>x', significado='<img src=x>'))
    db.session.commit()
    html = logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True)
    assert '</script><b>x' not in html and '<img src=x>' not in html
    assert any(p['en'] == '</script><b>x' for p in _palabras_de_la_pagina(html))


def test_las_palabras_salen_al_azar_sin_pesos(logged_client, user):
    _vocabulario(user)
    datos = _palabras_de_la_pagina(logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True))
    assert all(set(p) == {'id', 'en', 'es'} for p in datos)
    js = logged_client.get('/static/js/juegos.js').get_data(as_text=True)
    # Bolsa guardada en el navegador: ninguna palabra se repite hasta que salgan todas
    assert 'juegosUnirPendientes' in js and 'localStorage' in js
    assert 'peso' not in js and 'XP' not in js


# ── Resultado de una ronda ──

def test_guardar_ronda_sin_xp(logged_client, user):
    ids = [p.idVocab for p in _vocabulario(user)][:6]
    for _ in range(5):
        respuesta = _enviar(logged_client, ids, errores=2, segundos=41)
        assert respuesta.status_code == 200 and respuesta.get_json() == {'success': True}
    partida = JuegoPartida.query.first()
    assert (partida.juego, partida.parejas, partida.errores, partida.segundos) == ('unir', 6, 2, 41)
    assert partida.precision == 75  # 6 aciertos de 8 intentos
    assert JuegoPartida.query.count() == 5
    assert _xp(user) == 0  # los juegos no tocan el nivel



def test_no_se_aceptan_palabras_de_otra_persona(logged_client, user, other_user):
    mias = [p.idVocab for p in _vocabulario(user)][:3]
    ajena = Vocabulario(idUser=other_user.idUser, nombre='x', significado='y')
    db.session.add(ajena)
    db.session.commit()
    assert _enviar(logged_client, mias + [ajena.idVocab]).status_code == 400
    assert JuegoPartida.query.count() == 0


def test_resultados_invalidos(logged_client, user):
    ids = [p.idVocab for p in _vocabulario(user)]
    malos = [
        {'ids': ids[:3], 'errores': 0, 'segundos': 10},          # menos del mínimo
        {'ids': ids[:7], 'errores': 0, 'segundos': 10},          # más de una ronda
        {'ids': ids[:3] + ids[:1], 'errores': 0, 'segundos': 10},  # repetidas
        {'ids': ids[:4], 'errores': -1, 'segundos': 10},
        {'ids': ids[:4], 'errores': 0, 'segundos': 99999},
        {'ids': ids[:4], 'errores': '2', 'segundos': 10},
        {'ids': 'todo', 'errores': 0, 'segundos': 10},
        {},
    ]
    for datos in malos:
        assert logged_client.post('/menu/ingles/juegos/unir/resultado', json=datos).status_code == 400, datos
    assert logged_client.post('/menu/ingles/juegos/otro/resultado', json={}).status_code == 404
    assert JuegoPartida.query.count() == 0


def test_menu_muestra_el_resumen(logged_client, user):
    ids = [p.idVocab for p in _vocabulario(user)][:4]
    _enviar(logged_client, ids, errores=0, segundos=20)
    _enviar(logged_client, ids, errores=4, segundos=12)
    html = logged_client.get('/menu/ingles/juegos/').get_data(as_text=True)
    assert '2</span> rondas' in html
    assert '75%</span> precisión' in html   # (100 + 50) / 2
    assert '20s</span> mejor ronda perfecta' in html  # solo cuentan las rondas sin errores
    assert 'XP' not in html


def test_borrar_usuario_borra_sus_partidas(app, user):
    from app.routes.users_route import _delete_user_data
    db.session.add(JuegoPartida(idUser=user.idUser, juego='unir', parejas=4))
    db.session.commit()
    _delete_user_data(user.idUser)
    db.session.commit()
    assert JuegoPartida.query.count() == 0
