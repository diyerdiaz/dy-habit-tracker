"""Aviso obligatorio de medalla ganada: sale en cualquier pantalla, una medalla
a la vez, y cada una solo una vez (queda guardado en la base de datos)."""
import re

from app import db
from app.models.habitos import Habit
from app.models.medalla_anunciada import MedallaAnunciada
from app.services.cuentas import borrar_cuenta


def _crear_habito(user):
    """Crear un hábito desbloquea la medalla 'Arquitecto'."""
    db.session.add(Habit(idUser=user.idUser, habitName='Leer', habitFreq='Diario', habitCategory='Salud'))
    db.session.commit()


def _html(logged_client):
    resp = logged_client.get('/medallas/')
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_sin_medallas_nada_es_nuevo(logged_client):
    html = _html(logged_client)
    assert 'data-nueva="si"' not in html
    assert 'data-filtro="nuevas"' not in html


def test_la_pagina_marca_como_nueva_la_que_espera_su_aviso(logged_client, user):
    _crear_habito(user)
    html = _html(logged_client)
    assert 'data-nueva="si"' in html and '¡Nueva!' in html
    assert 'data-filtro="nuevas"' in html


def test_entrar_a_medallas_no_se_salta_el_aviso(logged_client, user):
    """Ver la página no cuenta como haber visto el aviso: sigue pendiente."""
    _crear_habito(user)
    _html(logged_client)
    _html(logged_client)
    assert [m['id'] for m in logged_client.get('/medallas/sin-ver').get_json()] == ['arquitecto']
    assert MedallaAnunciada.query.filter_by(idUser=user.idUser).count() == 0


def test_ya_anunciada_deja_de_ser_nueva(logged_client, user):
    _crear_habito(user)
    logged_client.post('/medallas/vista/arquitecto')
    html = _html(logged_client)
    assert 'data-nueva="si"' not in html
    assert 'data-filtro="nuevas"' not in html


def test_las_medallas_anunciadas_son_de_cada_usuario(logged_client, user, other_user):
    db.session.add(MedallaAnunciada(idUser=other_user.idUser, idMedalla='arquitecto'))
    db.session.commit()
    _crear_habito(user)
    assert [m['id'] for m in logged_client.get('/medallas/sin-ver').get_json()] == ['arquitecto']


def test_borrar_cuenta_borra_las_medallas_anunciadas(app, user):
    db.session.add(MedallaAnunciada(idUser=user.idUser, idMedalla='arquitecto'))
    db.session.commit()
    id_user = user.idUser
    borrar_cuenta(user)
    db.session.commit()
    assert MedallaAnunciada.query.filter_by(idUser=id_user).count() == 0


def test_aviso_sin_script_inline(logged_client, user):
    _crear_habito(user)
    html = _html(logged_client)
    assert 'js/medallas.js' in html and 'js/medallas_aviso.js' in html
    assert 'medallaAviso' not in ''.join(re.findall(r'<script>(.*?)</script>', html, re.S))


def test_el_aviso_es_obligatorio_solo_tiene_el_boton_de_aceptar(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    inicio = html.index('id="medallaAviso"')
    aviso = html[inicio:html.index('</div>\n</div>', inicio)]
    assert aviso.count('<button') == 1 and 'id="medallaAvisoOk"' in aviso
    assert '<a ' not in aviso
    # Empieza oculto: solo lo muestra el JS si hay medallas pendientes
    assert 'hidden' in html[inicio - 200:inicio + 300]


def test_un_aviso_aceptado_no_vuelve_tras_reiniciar_la_app(logged_client, user):
    """Se guarda en la base de datos, no en el navegador ni en memoria."""
    _crear_habito(user)
    logged_client.post('/medallas/vista/arquitecto')
    db.session.expire_all()
    assert db.session.get(MedallaAnunciada, (user.idUser, 'arquitecto')) is not None
    assert logged_client.get('/medallas/sin-ver').get_json() == []


# ── Aviso en cualquier pantalla, una medalla a la vez ──

def test_el_aviso_esta_en_cualquier_pantalla(logged_client):
    for ruta in ('/dashboard', '/tareas/', '/medallas/'):
        html = logged_client.get(ruta, follow_redirects=True).get_data(as_text=True)
        assert 'id="medallaAviso"' in html, ruta
        assert 'js/medallas_aviso.js' in html and 'css/medallas_aviso.css' in html


def test_sin_ver_requiere_login(client):
    assert client.get('/medallas/sin-ver').status_code == 302


def test_sin_ver_devuelve_la_medalla_recien_ganada(logged_client, user):
    assert logged_client.get('/medallas/sin-ver').get_json() == []
    _crear_habito(user)
    medallas = logged_client.get('/medallas/sin-ver').get_json()
    assert [m['id'] for m in medallas] == ['arquitecto']
    assert set(medallas[0]) == {'id', 'nombre', 'descripcion', 'frase', 'icono', 'rareza'}
    # Consultar no la marca: sigue pendiente hasta que se cierre el aviso
    assert logged_client.get('/medallas/sin-ver').get_json()[0]['id'] == 'arquitecto'


def test_marcar_vista_quita_la_medalla_del_aviso(logged_client, user):
    _crear_habito(user)
    assert logged_client.post('/medallas/vista/arquitecto').get_json() == {'ok': True}
    assert logged_client.get('/medallas/sin-ver').get_json() == []
    # Marcarla dos veces no duplica nada
    assert logged_client.post('/medallas/vista/arquitecto').status_code == 200
    assert MedallaAnunciada.query.filter_by(idUser=user.idUser).count() == 1


def test_no_se_marca_una_medalla_no_ganada_o_inexistente(logged_client, user):
    assert logged_client.post('/medallas/vista/arquitecto').status_code == 404
    assert logged_client.post('/medallas/vista/no_existe').status_code == 404
    assert MedallaAnunciada.query.filter_by(idUser=user.idUser).count() == 0


def test_marcar_un_habito_hace_aparecer_la_medalla(logged_client, user):
    """Al marcar el primer hábito del día se gana 'Primer Paso' y el aviso la recibe."""
    habit = Habit(idUser=user.idUser, habitName='Leer', habitFreq='Diario', habitCategory='Salud')
    db.session.add(habit)
    db.session.add(MedallaAnunciada(idUser=user.idUser, idMedalla='arquitecto'))
    db.session.commit()
    assert logged_client.get('/medallas/sin-ver').get_json() == []
    assert logged_client.post(f'/habit/{habit.idHabit}/toggle_today').status_code == 200
    ids = [m['id'] for m in logged_client.get('/medallas/sin-ver').get_json()]
    assert 'primer_paso' in ids


# ── Primero la frase del día, después las medallas ──

def test_la_frase_del_dia_va_antes_que_el_aviso_de_medallas(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert html.index('id="fraseDia"') < html.index('id="medallaAviso"')
    assert html.index('js/motivacion.js') < html.index('js/medallas_aviso.js')


def test_el_aviso_espera_a_que_se_cierre_la_frase():
    from pathlib import Path
    js = Path(__file__).resolve().parents[1] / 'static' / 'js'
    motivacion = (js / 'motivacion.js').read_text()
    aviso = (js / 'medallas_aviso.js').read_text()
    assert "dispatchEvent(new CustomEvent('frase-dia-cerrada'))" in motivacion
    assert "addEventListener('frase-dia-cerrada', mostrarSiguiente)" in aviso
    assert 'if (actual || fraseAbierta()) return;' in aviso
