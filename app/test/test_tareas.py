"""Tareas del día y tareas programadas para mañana u otra fecha."""
from datetime import date, timedelta

from app import db
from app.models.tareas import Tarea
from app.routes.tareas_route import _etiqueta_dia, MAX_DIAS_ADELANTE

HOY = date.today


def _agregar(client, descripcion, fecha=None):
    datos = {'descripcion': descripcion}
    if fecha is not None:
        datos['fecha'] = fecha
    return client.post('/tareas/add', data=datos)


def test_sin_fecha_la_tarea_es_de_hoy(logged_client, user):
    datos = _agregar(logged_client, 'Comprar pan').get_json()
    assert datos['success'] and datos['esHoy'] and datos['fecha'] == HOY().isoformat()
    assert db.session.get(Tarea, datos['id']).fecha == HOY()


def test_programar_para_manana(logged_client, user):
    manana = HOY() + timedelta(days=1)
    datos = _agregar(logged_client, 'Llamar al médico', manana.isoformat()).get_json()
    assert datos['success'] and not datos['esHoy']
    assert datos['label'] == 'Mañana'
    assert db.session.get(Tarea, datos['id']).fecha == manana


def test_programar_en_fecha_del_calendario(logged_client, user):
    fecha = HOY() + timedelta(days=10)
    datos = _agregar(logged_client, 'Entregar informe', fecha.isoformat()).get_json()
    assert datos['success']
    assert datos['label'].endswith(fecha.strftime('%d/%m/%Y'))
    assert db.session.get(Tarea, datos['id']).fecha == fecha


def test_rechaza_fechas_pasadas_invalidas_o_muy_lejanas(logged_client, user):
    for fecha in ((HOY() - timedelta(days=1)).isoformat(), '2026-13-40', 'mañana',
                  (HOY() + timedelta(days=MAX_DIAS_ADELANTE + 1)).isoformat()):
        respuesta = _agregar(logged_client, 'X', fecha)
        assert respuesta.status_code == 400, fecha
        assert 'fecha' in respuesta.get_json()['error']
    assert Tarea.query.count() == 0
    assert _agregar(logged_client, 'Límite', (HOY() + timedelta(days=MAX_DIAS_ADELANTE)).isoformat()).status_code == 200


def test_pagina_separa_hoy_de_manana(logged_client, user):
    _agregar(logged_client, 'Tarea de hoy')
    _agregar(logged_client, 'Tarea de mañana', (HOY() + timedelta(days=1)).isoformat())
    _agregar(logged_client, 'Tarea lejana', (HOY() + timedelta(days=5)).isoformat())
    html = logged_client.get('/tareas/').get_data(as_text=True)

    lista_hoy = html[html.index('id="tareasList"'):html.index('id="tareasEmpty"')]
    assert 'Tarea de hoy' in lista_hoy and 'Tarea de mañana' not in lista_hoy

    # Abajo solo se listan las de mañana; las de días más lejanos no
    manana = html[html.index('id="proximasPanel"'):html.index('js/tareas.js')]
    assert 'Tareas de mañana' in manana and 'Tarea de mañana' in manana
    assert 'Tarea lejana' not in html
    # ...pero siguen marcadas en el calendario
    assert f'"{(HOY() + timedelta(days=5)).isoformat()}": 1' in html


def test_ver_historial_oculta_fechas_calendario_y_manana(logged_client, user):
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert "classList.toggle('viendo-historial', abierto)" in js
    css = logged_client.get('/static/css/tareas.css').get_data(as_text=True)
    for selector in ('#fechaSelector', '#calendarioPanel', '#proximasPanel'):
        assert f'.tareas-wrapper.viendo-historial {selector}' in css


def test_sin_proximas_la_seccion_queda_oculta(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert 'id="proximasPanel" hidden' in html


def test_selector_de_fecha_y_calendario_grande(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    hoy, manana = HOY().isoformat(), (HOY() + timedelta(days=1)).isoformat()
    assert f'data-fecha="{hoy}">Hoy<' in html and f'data-fecha="{manana}">Mañana<' in html
    # "Otra fecha" abre un calendario propio (no el selector pequeño del navegador)
    assert 'aria-controls="calendarioPanel"' in html and 'id="calDias"' in html
    assert 'type="date"' not in html
    maxima = (HOY() + timedelta(days=MAX_DIAS_ADELANTE)).isoformat()
    assert f'data-maxima="{maxima}"' in html
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert "'&fecha='" in js and 'pintarCalendario' in js and 'sumarConteo' in js


def test_ver_historial_queda_arriba_de_hoy_manana_otra_fecha(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert html.index('id="addTaskForm"') < html.index('id="toggleHistBtn"') < html.index('id="fechaSelector"')
    # El panel del historial se abre justo debajo de su botón
    assert html.index('id="toggleHistBtn"') < html.index('id="historialPanel"') < html.index('id="fechaSelector"')


def test_calendario_recibe_cuantas_tareas_hay_por_dia(logged_client, user):
    import json, re
    _agregar(logged_client, 'Hoy 1')
    _agregar(logged_client, 'Hoy 2')
    dentro_de_3 = (HOY() + timedelta(days=3)).isoformat()
    _agregar(logged_client, 'Futura', dentro_de_3)
    # Las de días pasados no se marcan
    db.session.add(Tarea(idUser=user.idUser, descripcion='Vieja', fecha=HOY() - timedelta(days=2)))
    db.session.commit()
    html = logged_client.get('/tareas/').get_data(as_text=True)
    conteos = json.loads(re.search(r"data-conteos='([^']*)'", html).group(1))
    assert conteos == {HOY().isoformat(): 2, dentro_de_3: 1}


def test_cuando_llega_el_dia_pasa_a_tareas_de_hoy(logged_client, user):
    # Una tarea programada antes para hoy aparece en la lista principal
    db.session.add(Tarea(idUser=user.idUser, descripcion='Programada antes', fecha=HOY()))
    db.session.commit()
    html = logged_client.get('/tareas/').get_data(as_text=True)
    lista_hoy = html[html.index('id="tareasList"'):html.index('id="tareasEmpty"')]
    assert 'Programada antes' in lista_hoy


def test_proximas_de_otro_usuario_no_se_ven(logged_client, user, other_user):
    db.session.add(Tarea(idUser=other_user.idUser, descripcion='Ajena', fecha=HOY() + timedelta(days=2)))
    db.session.commit()
    assert 'Ajena' not in logged_client.get('/tareas/').get_data(as_text=True)


def test_completar_y_borrar_tarea_programada(logged_client, user):
    id_tarea = _agregar(logged_client, 'Futura', (HOY() + timedelta(days=3)).isoformat()).get_json()['id']
    assert logged_client.post(f'/tareas/{id_tarea}/toggle').get_json()['completada'] is True
    assert logged_client.post(f'/tareas/{id_tarea}/delete').get_json()['success']
    assert db.session.get(Tarea, id_tarea) is None


def test_etiqueta_dia():
    hoy = date(2026, 10, 26)  # lunes
    assert _etiqueta_dia(hoy, hoy) == 'Hoy'
    assert _etiqueta_dia(date(2026, 10, 27), hoy) == 'Mañana'
    assert _etiqueta_dia(date(2026, 10, 29), hoy) == 'Jueves 29/10/2026'


# ── Editar ──

def test_editar_el_texto_de_una_tarea(logged_client, user):
    id_tarea = _agregar(logged_client, 'Comprar pna').get_json()['id']
    datos = logged_client.post(f'/tareas/{id_tarea}/editar', data={'descripcion': '  Comprar pan  '}).get_json()
    assert datos == {'success': True, 'descripcion': 'Comprar pan'}
    assert db.session.get(Tarea, id_tarea).descripcion == 'Comprar pan'


def test_editar_no_deja_texto_vacio_ni_tareas_ajenas(logged_client, user, other_user):
    id_tarea = _agregar(logged_client, 'Original').get_json()['id']
    assert logged_client.post(f'/tareas/{id_tarea}/editar', data={'descripcion': '   '}).status_code == 400
    assert logged_client.post(f'/tareas/{id_tarea}/editar', data={'descripcion': 'x' * 256}).status_code == 400
    assert db.session.get(Tarea, id_tarea).descripcion == 'Original'
    ajena = Tarea(idUser=other_user.idUser, descripcion='Ajena', fecha=HOY())
    db.session.add(ajena)
    db.session.commit()
    assert logged_client.post(f'/tareas/{ajena.idTarea}/editar', data={'descripcion': 'Hackeada'}).status_code == 404
    assert db.session.get(Tarea, ajena.idTarea).descripcion == 'Ajena'


def test_cada_tarea_tiene_botones_de_editar_y_recordatorio(logged_client, user):
    _agregar(logged_client, 'Con botones')
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert 'class="tarea-btn tarea-editar"' in html and 'class="tarea-btn tarea-recordar"' in html
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert '/editar`' in js and '/recordatorio`' in js


# ── Recordatorio por correo ──

def test_poner_y_quitar_recordatorio(logged_client, user):
    id_tarea = _agregar(logged_client, 'Llamar').get_json()['id']
    datos = logged_client.post(f'/tareas/{id_tarea}/recordatorio', data={'hora': '20:30'}).get_json()
    assert datos['success'] and datos['hora'] == '20:30' and datos['horaTexto'] == '8:30 p. m.'
    tarea = db.session.get(Tarea, id_tarea)
    assert tarea.horaRecordatorio == '20:30' and tarea.recordatorioEnviado is False
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert 'data-hora="20:30"' in html and '8:30 p. m.' in html

    datos = logged_client.post(f'/tareas/{id_tarea}/recordatorio', data={'hora': ''}).get_json()
    assert datos['success'] and datos['hora'] is None
    assert db.session.get(Tarea, id_tarea).horaRecordatorio is None


def test_recordatorio_rechaza_horas_invalidas(logged_client, user):
    id_tarea = _agregar(logged_client, 'X').get_json()['id']
    for hora in ('25:00', '8pm', '12:60', 'abc'):
        assert logged_client.post(f'/tareas/{id_tarea}/recordatorio', data={'hora': hora}).status_code == 400, hora


def test_recordatorio_avisa_si_no_hay_correo(logged_client, user):
    user.email = None
    db.session.commit()
    id_tarea = _agregar(logged_client, 'X').get_json()['id']
    assert logged_client.post(f'/tareas/{id_tarea}/recordatorio', data={'hora': '09:00'}).get_json()['sinCorreo'] is True
    user.email = 'yo@test.com'
    db.session.commit()
    assert logged_client.post(f'/tareas/{id_tarea}/recordatorio', data={'hora': '09:00'}).get_json()['sinCorreo'] is False


def test_cambiar_la_hora_permite_otro_envio(logged_client, user):
    id_tarea = _agregar(logged_client, 'X').get_json()['id']
    tarea = db.session.get(Tarea, id_tarea)
    tarea.horaRecordatorio, tarea.recordatorioEnviado = '09:00', True
    db.session.commit()
    logged_client.post(f'/tareas/{id_tarea}/recordatorio', data={'hora': '18:00'})
    assert db.session.get(Tarea, id_tarea).recordatorioEnviado is False


def test_hora_texto():
    assert Tarea(horaRecordatorio='00:05').hora_texto() == '12:05 a. m.'
    assert Tarea(horaRecordatorio='12:00').hora_texto() == '12:00 p. m.'
    assert Tarea(horaRecordatorio=None).hora_texto() == ''
