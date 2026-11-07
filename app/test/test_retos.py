"""Retos con XP apostado que el admin le pone a cada usuario."""
import os
import re
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app import db
from app.models.retos import Reto, RetoDia, PENDIENTE, EN_CURSO, GANADO, PERDIDO, RECHAZADO, VENCIDO, CANCELADO
from app.models.user_progress import UserProgress
from app.models.users import User, ROL_ADMIN
from app.services import retos as servicio
from app.services.cuentas import borrar_cuenta
from app.services.esquema import actualizar_esquema
from app.services.gamificacion import get_or_create_progress

HOY = date.today()
CLAVE_ADMIN = 'Admin_clave1!'
INICIO = date(2026, 12, 1)
FIN = date(2026, 12, 3)


@pytest.fixture
def admin_client(app):
    admin = User(nameUser='jefe', password=CLAVE_ADMIN, rol=ROL_ADMIN)
    db.session.add(admin)
    db.session.commit()
    cliente = app.test_client()
    cliente.post('/', data={'nameUser': 'jefe', 'passwordUser': CLAVE_ADMIN})
    return cliente


def _reto(user, inicio=INICIO, fin=FIN, apuesta=500, estado=PENDIENTE, nombre='No ver redes sociales'):
    reto = Reto(idUser=user.idUser, nombre=nombre, fechaInicio=inicio, fechaFin=fin, apuesta=apuesta, estado=estado)
    db.session.add(reto)
    db.session.commit()
    return reto


def _con_xp(user, xp):
    get_or_create_progress(user.idUser).xpTotal = xp
    db.session.commit()


def _xp(user):
    progreso = db.session.get(UserProgress, user.idUser)
    return progreso.xpTotal if progreso else 0


# ── Validación del formulario del admin ──

@pytest.mark.parametrize('nombre, inicio, fin, apuesta, mensaje', [
    ('', HOY, HOY, 100, 'nombre'),
    ('Reto', HOY - timedelta(days=1), HOY, 100, 'ya pasó'),
    ('Reto', HOY, HOY - timedelta(days=1), 100, 'posterior'),
    ('Reto', HOY, HOY + timedelta(days=servicio.MAX_DIAS), 100, 'máximo'),
    ('Reto', HOY, HOY, -5, 'apuesta'),
    ('Reto', HOY, HOY, None, 'apuesta'),
    ('Reto', None, HOY, 100, 'fecha'),
])
def test_validar_reto(app, nombre, inicio, fin, apuesta, mensaje):
    assert mensaje in servicio.validar_reto(nombre, '', inicio, fin, apuesta)


def test_reto_valido(app):
    assert servicio.validar_reto('Reto', '', HOY, HOY + timedelta(days=4), 500) is None


# ── Admin ──

def test_admin_envia_un_reto(admin_client, user):
    resp = admin_client.post(f'/admin/usuarios/{user.idUser}/retos', data={
        'nombre': 'No ver redes sociales', 'descripcion': '5 días sin Instagram',
        'inicio': HOY.isoformat(), 'fin': (HOY + timedelta(days=4)).isoformat(), 'apuesta': '500'})
    assert resp.status_code == 302 and resp.headers['Location'].endswith('#retos')
    reto = Reto.query.one()
    assert (reto.idUser, reto.estado, reto.apuesta, reto.total_dias()) == (user.idUser, PENDIENTE, 500, 5)


def test_admin_no_envia_un_reto_invalido(admin_client, user):
    admin_client.post(f'/admin/usuarios/{user.idUser}/retos', data={
        'nombre': 'Reto', 'inicio': (HOY - timedelta(days=1)).isoformat(), 'fin': HOY.isoformat(), 'apuesta': '500'})
    assert Reto.query.count() == 0


def test_detalle_del_admin_muestra_los_retos(admin_client, user):
    _reto(user, nombre='Sin azúcar')
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert 'id="retos"' in html and 'Sin azúcar' in html and 'Enviar reto' in html and 'Cancelar' in html


def test_admin_cancela_sin_cambiar_el_xp(admin_client, user):
    _con_xp(user, 300)
    reto = _reto(user, inicio=HOY, fin=HOY + timedelta(days=2), estado=EN_CURSO)
    admin_client.post(f'/admin/usuarios/{user.idUser}/retos/{reto.idReto}/cancelar')
    assert db.session.get(Reto, reto.idReto).estado == CANCELADO and _xp(user) == 300


def test_no_se_cancela_un_reto_terminado(app, user):
    reto = _reto(user, estado=GANADO)
    assert servicio.cancelar(reto) is False and reto.estado == GANADO


def test_usuario_normal_no_usa_las_rutas_del_admin(logged_client, user, other_user):
    resp = logged_client.post(f'/admin/usuarios/{other_user.idUser}/retos', data={
        'nombre': 'Reto', 'inicio': HOY.isoformat(), 'fin': HOY.isoformat(), 'apuesta': '10'})
    assert resp.status_code == 404 and Reto.query.count() == 0


# ── El botón "Retos" del menú ──

def test_sin_retos_no_hay_boton(logged_client):
    assert 'href="/retos/"' not in logged_client.get('/dashboard').get_data(as_text=True)


def test_con_un_reto_aparece_el_boton_en_el_menu(logged_client, user):
    _reto(user, inicio=HOY, fin=HOY + timedelta(days=2))
    for url in ('/dashboard', '/register_habit', '/medallas/'):
        assert 'href="/retos/"' in logged_client.get(url).get_data(as_text=True), url


def test_rechazar_quita_el_boton_y_no_cuesta_nada(logged_client, user):
    _con_xp(user, 200)
    reto = _reto(user, inicio=HOY, fin=HOY + timedelta(days=2))
    resp = logged_client.post(f'/retos/{reto.idReto}/rechazar', follow_redirects=True)
    assert db.session.get(Reto, reto.idReto).estado == RECHAZADO and _xp(user) == 200
    assert 'href="/retos/"' not in resp.get_data(as_text=True)


def test_el_resultado_se_ve_una_vez_y_luego_el_boton_se_va(logged_client, user):
    _reto(user, estado=GANADO)
    assert 'href="/retos/"' in logged_client.get('/dashboard').get_data(as_text=True)
    assert 'Cumplido · +500 XP' in logged_client.get('/retos/').get_data(as_text=True)
    assert 'href="/retos/"' not in logged_client.get('/dashboard').get_data(as_text=True)


# ── Aceptar, rechazar y marcar desde la página ──

def test_pagina_muestra_aceptar_y_rechazar(logged_client, user):
    _reto(user, inicio=HOY, fin=HOY + timedelta(days=4))
    html = logged_client.get('/retos/').get_data(as_text=True)
    assert 'No ver redes sociales' in html and 'Aceptar reto' in html and 'Rechazar' in html
    assert '500' in html


def test_aceptar_y_cumplir_hoy(logged_client, user):
    reto = _reto(user, inicio=HOY, fin=HOY + timedelta(days=4))
    logged_client.post(f'/retos/{reto.idReto}/aceptar')
    assert db.session.get(Reto, reto.idReto).estado == EN_CURSO
    assert 'Cumplí hoy' in logged_client.get('/retos/').get_data(as_text=True)
    logged_client.post(f'/retos/{reto.idReto}/cumplir')
    assert RetoDia.query.filter_by(idReto=reto.idReto, fecha=HOY).count() == 1
    # Otro clic quita la marca de hoy
    logged_client.post(f'/retos/{reto.idReto}/cumplir')
    assert RetoDia.query.count() == 0


def test_no_se_marca_antes_de_que_empiece(logged_client, user):
    reto = _reto(user, inicio=HOY + timedelta(days=2), fin=HOY + timedelta(days=4), estado=EN_CURSO)
    resp = logged_client.post(f'/retos/{reto.idReto}/cumplir', follow_redirects=True)
    assert 'empieza el' in resp.get_data(as_text=True) and RetoDia.query.count() == 0


def test_no_se_toca_el_reto_de_otro(logged_client, other_user):
    ajeno = _reto(other_user, inicio=HOY, fin=HOY)
    for accion in ('aceptar', 'rechazar', 'cumplir'):
        assert logged_client.post(f'/retos/{ajeno.idReto}/{accion}').status_code == 404
    assert db.session.get(Reto, ajeno.idReto).estado == PENDIENTE


# ── Reglas: ganar, perder y vencer ──

def test_cumplir_todos_los_dias_gana_la_apuesta(app, user):
    _con_xp(user, 100)
    reto = _reto(user)
    assert servicio.responder(reto, True, hoy=date(2026, 11, 30)) is None
    for dia in (INICIO, INICIO + timedelta(days=1)):
        servicio.cumplir_hoy(reto, hoy=dia)
        assert reto.estado == EN_CURSO
    servicio.cumplir_hoy(reto, hoy=FIN)   # el último día lo gana en ese momento
    assert reto.estado == GANADO and _xp(user) == 600


def test_un_dia_sin_marcar_pierde_la_apuesta(app, user):
    _con_xp(user, 800)
    reto = _reto(user, estado=EN_CURSO)
    servicio.cumplir_hoy(reto, hoy=INICIO)
    # Llega el tercer día y el segundo quedó sin marcar
    servicio.actualizar_retos(user.idUser, hoy=FIN)
    assert db.session.get(Reto, reto.idReto).estado == PERDIDO and _xp(user) == 300


def test_el_dia_de_hoy_no_cuenta_como_fallado_hasta_que_termina(app, user):
    reto = _reto(user, estado=EN_CURSO)
    servicio.actualizar_retos(user.idUser, hoy=INICIO)
    assert reto.estado == EN_CURSO


def test_perder_no_deja_el_xp_en_negativo(app, user):
    _con_xp(user, 100)
    reto = _reto(user, estado=EN_CURSO)
    servicio.actualizar_retos(user.idUser, hoy=FIN + timedelta(days=1))
    assert reto.estado == PERDIDO and _xp(user) == 0


def test_se_puede_aceptar_hasta_el_dia_de_inicio(app, user):
    reto = _reto(user)
    assert servicio.responder(reto, True, hoy=INICIO) is None and reto.estado == EN_CURSO


def test_sin_responder_vence_sin_perder_nada(app, user):
    _con_xp(user, 400)
    reto = _reto(user)
    assert 'ya no espera' in servicio.responder(reto, True, hoy=INICIO + timedelta(days=1))
    assert reto.estado == VENCIDO and _xp(user) == 400


def test_reto_terminado_no_se_marca(app, user):
    reto = _reto(user, estado=PERDIDO)
    marcado, error = servicio.cumplir_hoy(reto, hoy=INICIO)
    assert not marcado and 'terminó' in error


def test_reto_sin_apuesta_no_cambia_el_xp(app, user):
    _con_xp(user, 50)
    reto = _reto(user, apuesta=0, estado=EN_CURSO, inicio=INICIO, fin=INICIO)
    servicio.cumplir_hoy(reto, hoy=INICIO)
    assert reto.estado == GANADO and _xp(user) == 50


def test_borrar_la_cuenta_borra_sus_retos(app, user):
    reto = _reto(user, estado=EN_CURSO)
    servicio.cumplir_hoy(reto, hoy=INICIO)
    borrar_cuenta(user)
    db.session.commit()
    assert Reto.query.count() == 0 and RetoDia.query.count() == 0


def test_funciona_aunque_exista_la_tabla_retos_de_un_intento_anterior(app, logged_client, user):
    """Algunas bases locales tienen una tabla 'retos' vieja con otras columnas
    (titulo, xp, castigo...): los retos nuevos usan sus propias tablas."""
    db.session.execute(text(
        'CREATE TABLE IF NOT EXISTS retos ("idReto" INTEGER PRIMARY KEY, "idUser" INTEGER NOT NULL, '
        'titulo VARCHAR(120) NOT NULL, xp INTEGER NOT NULL)'))
    db.session.execute(text("INSERT INTO retos (\"idUser\", titulo, xp) VALUES (:u, 'viejo', 500)"), {'u': user.idUser})
    db.session.commit()
    actualizar_esquema()
    _reto(user, inicio=HOY, fin=HOY)
    assert logged_client.get('/dashboard').status_code == 200
    assert 'No ver redes sociales' in logged_client.get('/retos/').get_data(as_text=True)
    # La tabla vieja no se toca
    assert db.session.execute(text('SELECT titulo FROM retos')).scalar() == 'viejo'


# ── Página: historial, semanas y animación al aceptar ──

def test_historial_muestra_si_se_cumplio_o_no(logged_client, user):
    ganado = _reto(user, nombre='Sin azúcar', estado=GANADO)
    _reto(user, nombre='Sin redes', estado=PERDIDO, apuesta=300)
    _reto(user, nombre='Cancelado por el admin', estado=CANCELADO)
    db.session.add(RetoDia(idReto=ganado.idReto, idUser=user.idUser, fecha=INICIO))
    db.session.commit()
    html = logged_client.get('/retos/').get_data(as_text=True)
    historial = html.split('class="retos-historial"', 1)[1].split('class="retos-actuales"', 1)[0]
    assert 'Sin azúcar' in historial and 'Cumplido · +500 XP' in historial and '1/3 días' in historial
    assert 'Sin redes' in historial and 'No cumplido · −300 XP' in historial
    assert 'Cancelado · sin XP' in historial
    assert '1 cumplidos' in historial and '1 no cumplidos' in historial


def test_historial_vacio(logged_client, user):
    _reto(user, inicio=HOY, fin=HOY)
    assert 'Aquí verás los retos que termines' in logged_client.get('/retos/').get_data(as_text=True)


def test_los_dias_van_en_semanas_con_su_dia(logged_client, user):
    _reto(user, inicio=HOY, fin=HOY + timedelta(days=9), estado=EN_CURSO)
    html = logged_client.get('/retos/').get_data(as_text=True)
    assert len(re.findall(r'class="reto-dia[ "]', html)) == 10
    letra = ['L', 'M', 'X', 'J', 'V', 'S', 'D'][HOY.weekday()]
    assert f'<small>{letra}</small>{HOY.day}' in html


def test_aceptar_lleva_la_animacion(logged_client, user):
    _reto(user, inicio=HOY, fin=HOY, nombre='Sin redes')
    html = logged_client.get('/retos/').get_data(as_text=True)
    assert 'data-iniciar-reto="Sin redes"' in html and 'id="retoInicio"' in html and 'js/retos.js' in html


def test_css_de_los_dias_en_siete_columnas(app):
    with open(os.path.join(app.static_folder, 'css', 'retos.css'), encoding='utf-8') as f:
        assert 'grid-template-columns: repeat(7, minmax(0, 1fr))' in f.read()


# ── Todo o nada: apostar todo el XP ──

def test_admin_envia_un_reto_de_todo_el_xp(admin_client, user):
    admin_client.post(f'/admin/usuarios/{user.idUser}/retos', data={
        'nombre': 'Todo o nada', 'inicio': HOY.isoformat(), 'fin': HOY.isoformat(), 'modo_apuesta': 'todo'})
    reto = Reto.query.one()
    assert reto.todoXp and reto.apuesta == 0


def test_formulario_del_admin_ofrece_cantidad_o_todo(admin_client, user):
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert 'value="cantidad" checked' in html and 'value="todo"' in html and 'Todo su XP' in html


def test_todo_el_xp_se_fija_al_aceptar_y_gana_el_doble(app, user):
    _con_xp(user, 1200)
    reto = servicio.crear_reto(user, 'Todo o nada', '', INICIO, INICIO, None, todo=True)
    _con_xp(user, 1500)   # ganó más XP antes de aceptar: cuenta el de ese momento
    servicio.responder(reto, True, hoy=INICIO)
    assert reto.apuesta == 1500
    servicio.cumplir_hoy(reto, hoy=INICIO)
    assert reto.estado == GANADO and _xp(user) == 3000


def test_todo_el_xp_y_perder_lo_deja_en_cero(app, user):
    _con_xp(user, 900)
    reto = servicio.crear_reto(user, 'Todo o nada', '', INICIO, FIN, None, todo=True)
    servicio.responder(reto, True, hoy=INICIO)
    servicio.actualizar_retos(user.idUser, hoy=FIN)
    assert reto.estado == PERDIDO and _xp(user) == 0


def test_pagina_muestra_todo_o_nada_con_su_xp(logged_client, user):
    _con_xp(user, 750)
    servicio.crear_reto(user, 'Sin redes', '', HOY, HOY, None, todo=True)
    html = logged_client.get('/retos/').get_data(as_text=True)
    assert 'Todo o nada' in html and '<span>750</span> XP en juego' in html
    assert 'todo tu XP</strong> (750 XP ahora)' in html and 'data-todo-xp' in html


def test_reto_de_cantidad_no_es_todo_o_nada(logged_client, user):
    _reto(user, inicio=HOY, fin=HOY)
    html = logged_client.get('/retos/').get_data(as_text=True)
    assert 'data-todo-xp' not in html and 'Todo o nada' not in html


def test_animacion_tiene_frases_al_azar(app):
    with open(os.path.join(app.static_folder, 'js', 'retos.js'), encoding='utf-8') as f:
        js = f.read()
    assert 'Math.random()' in js and 'FRASES_TODO' in js and js.count("',\n") >= 5


# ── Fechas del formulario del admin ──

def test_admin_no_puede_terminar_un_reto_antes_de_que_empiece(admin_client, user):
    resp = admin_client.post(f'/admin/usuarios/{user.idUser}/retos', data={
        'nombre': 'Reto', 'inicio': (HOY + timedelta(days=5)).isoformat(),
        'fin': HOY.isoformat(), 'apuesta': '500'}, follow_redirects=True)
    assert Reto.query.count() == 0
    assert 'La fecha de fin debe ser igual o posterior a la de inicio.' in resp.get_data(as_text=True)


def test_el_calendario_de_fin_sigue_al_de_inicio(admin_client, user, app):
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert 'id="retoInicio"' in html and 'id="retoFin"' in html
    assert 'placeholder="Ej.: no ver redes sociales"' in html
    with open(os.path.join(app.static_folder, 'js', 'admin.js'), encoding='utf-8') as f:
        js = f.read()
    assert 'fin.min = inicio.value' in js


# ── Historial de 7 en 7 ──

def _historial_de(html):
    return html.split('class="retos-historial"', 1)[1].split('class="retos-actuales"', 1)[0]


def _muchos_terminados(user, cuantos):
    """Retos terminados con fechas distintas: el 1 es el más reciente."""
    for i in range(1, cuantos + 1):
        inicio = INICIO - timedelta(days=10 * i)
        _reto(user, nombre=f'Reto número {i:02d}', inicio=inicio, fin=inicio + timedelta(days=2),
              estado=GANADO if i % 2 else PERDIDO)


def test_historial_muestra_siete_por_pagina(logged_client, user):
    _muchos_terminados(user, 16)
    historial = _historial_de(logged_client.get('/retos/').get_data(as_text=True))
    assert historial.count('class="reto-fila estado') == 7
    assert 'Reto número 01' in historial and 'Reto número 07' in historial and 'Reto número 08' not in historial
    assert '1 de 3' in historial and 'Siguiente' in historial and 'Anterior' not in historial
    # Los contadores cuentan todos, no solo los de la página
    assert '8 cumplidos' in historial and '8 no cumplidos' in historial


def test_siguiente_y_anterior(logged_client, user):
    _muchos_terminados(user, 16)
    segunda = _historial_de(logged_client.get('/retos/?pagina=2').get_data(as_text=True))
    assert 'Reto número 08' in segunda and 'Reto número 14' in segunda and 'Reto número 07' not in segunda
    assert '2 de 3' in segunda and 'href="/retos/?pagina=1"' in segunda and 'href="/retos/?pagina=3"' in segunda
    ultima = _historial_de(logged_client.get('/retos/?pagina=3').get_data(as_text=True))
    assert ultima.count('class="reto-fila estado') == 2 and 'Siguiente' not in ultima and 'Anterior' in ultima


def test_pagina_fuera_de_rango_muestra_la_mas_cercana(logged_client, user):
    _muchos_terminados(user, 9)
    assert '2 de 2' in _historial_de(logged_client.get('/retos/?pagina=99').get_data(as_text=True))
    assert '1 de 2' in _historial_de(logged_client.get('/retos/?pagina=-4').get_data(as_text=True))
    assert '1 de 2' in _historial_de(logged_client.get('/retos/?pagina=abc').get_data(as_text=True))


def test_con_siete_o_menos_no_hay_botones(logged_client, user):
    _muchos_terminados(user, 7)
    historial = _historial_de(logged_client.get('/retos/').get_data(as_text=True))
    assert historial.count('class="reto-fila estado') == 7 and 'historial-paginas' not in historial
