"""Anuncio de medallas nuevas: al entrar a Medallas se avisa cuáles se ganaron
desde la última visita, una sola vez."""
import re

from app import db
from app.models.habitos import Habit
from app.models.medalla_vista import MedallaVista
from app.services.cuentas import borrar_cuenta


def _crear_habito(user):
    """Crear un hábito desbloquea la medalla 'Arquitecto'."""
    db.session.add(Habit(idUser=user.idUser, habitName='Leer', habitFreq='Diario', habitCategory='Salud'))
    db.session.commit()


def _html(logged_client):
    resp = logged_client.get('/medallas/')
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_sin_medallas_no_hay_anuncio(logged_client):
    html = _html(logged_client)
    assert 'id="medallasAnuncio"' not in html
    assert 'data-filtro="nuevas"' not in html


def test_anuncia_la_medalla_ganada(logged_client, user):
    _crear_habito(user)
    html = _html(logged_client)
    assert 'id="medallasAnuncio"' in html
    assert '¡Ganaste 1 medalla nueva!' in html
    anuncio = html[html.index('id="medallasAnuncio"'):html.index('class="medallas-resumen"')]
    assert 'Arquitecto' in anuncio
    # La tarjeta queda marcada como nueva y aparece el filtro "Nuevas"
    assert 'data-nueva="si"' in html and '¡Nueva!' in html
    assert 'data-filtro="nuevas"' in html


def test_el_anuncio_sale_una_sola_vez(logged_client, user):
    _crear_habito(user)
    _html(logged_client)
    html = _html(logged_client)
    assert 'id="medallasAnuncio"' not in html
    assert 'data-nueva="si"' not in html
    assert MedallaVista.query.filter_by(idUser=user.idUser, idMedalla='arquitecto').count() == 1


def test_solo_anuncia_las_que_faltan_por_ver(logged_client, user):
    db.session.add(MedallaVista(idUser=user.idUser, idMedalla='arquitecto'))
    db.session.commit()
    _crear_habito(user)
    assert 'id="medallasAnuncio"' not in _html(logged_client)


def test_las_medallas_vistas_son_de_cada_usuario(logged_client, user, other_user):
    db.session.add(MedallaVista(idUser=other_user.idUser, idMedalla='arquitecto'))
    db.session.commit()
    _crear_habito(user)
    assert '¡Ganaste 1 medalla nueva!' in _html(logged_client)


def test_borrar_cuenta_borra_las_medallas_vistas(app, user):
    db.session.add(MedallaVista(idUser=user.idUser, idMedalla='arquitecto'))
    db.session.commit()
    id_user = user.idUser
    borrar_cuenta(user)
    db.session.commit()
    assert MedallaVista.query.filter_by(idUser=id_user).count() == 0


def test_anuncio_sin_script_inline(logged_client, user):
    _crear_habito(user)
    html = _html(logged_client)
    assert 'js/medallas.js' in html
    assert 'medallasAnuncio' not in ''.join(re.findall(r'<script>(.*?)</script>', html, re.S))
