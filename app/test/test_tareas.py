"""Tareas del día y tareas programadas para mañana u otra fecha."""
import re
from datetime import date, datetime, timedelta

from app import db
from app.models.tareas import Tarea
from app.routes.tareas_route import _etiqueta_dia, MAX_DIAS_ADELANTE, SEGUNDOS_DUPLICADO

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

    # Mañana tiene su propia lista, sin las de otros días
    manana = html[html.index('id="proximasPanel"'):html.index('id="otraFechaPanel"')]
    assert 'Tareas de mañana' in manana and 'Tarea de mañana' in manana
    assert 'Tarea lejana' not in manana
    # Las de días más lejanos van en el grupo de su día (se ve al elegirlo)...
    lejana = (HOY() + timedelta(days=5)).isoformat()
    otras = html[html.index('id="otraFechaPanel"'):html.index('js/tareas.js')]
    assert f'data-fecha="{lejana}" hidden' in otras and 'Tarea lejana' in otras
    # ...y siguen marcadas en el calendario
    assert f'"{(HOY() + timedelta(days=5)).isoformat()}": 1' in html


def test_ver_historial_oculta_fechas_calendario_y_manana(logged_client, user):
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert "classList.toggle('viendo-historial', abierto)" in js
    css = logged_client.get('/static/css/tareas.css').get_data(as_text=True)
    for selector in ('#fechaSelector', '#calendarioPanel', '#proximasPanel',
                     '#addTaskForm', '#tareasList', '#tareasEmpty'):
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


def test_tarea_programada_no_se_marca_pero_se_borra(logged_client, user):
    id_tarea = _agregar(logged_client, 'Futura', (HOY() + timedelta(days=3)).isoformat()).get_json()['id']
    assert logged_client.post(f'/tareas/{id_tarea}/toggle').status_code == 400
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


def test_tamano_de_letra_ajustable(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert 'id="letraMenos"' in html and 'id="letraMas"' in html

    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert "setProperty('--tarea-escala'" in js
    assert 'localStorage.setItem(CLAVE_LETRA' in js

    css = logged_client.get('/static/css/tareas.css').get_data(as_text=True)
    assert 'var(--tarea-escala, 1)' in css
    # Ya no corta palabras por la mitad ("habitacio / n")
    texto = css[css.index('.tarea-text {'):]
    texto = texto[:texto.index('}')]
    assert 'word-break: break-word' not in texto and 'overflow-wrap: break-word' in texto


def test_no_se_puede_marcar_una_tarea_de_otro_dia(logged_client, user):
    hoy_id = _agregar(logged_client, 'De hoy').get_json()['id']
    manana_id = _agregar(logged_client, 'De mañana', (HOY() + timedelta(days=1)).isoformat()).get_json()['id']

    respuesta = logged_client.post(f'/tareas/{manana_id}/toggle')
    assert respuesta.status_code == 400 and 'otro día' in respuesta.get_json()['error']
    assert db.session.get(Tarea, manana_id).completada is False

    assert logged_client.post(f'/tareas/{hoy_id}/toggle').get_json()['completada'] is True

    # En la página, la de mañana sale marcada como futura y la de hoy no
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert f'futura" data-id="{manana_id}"' in html
    assert f'futura" data-id="{hoy_id}"' not in html


def test_la_tarea_de_manana_se_puede_marcar_cuando_llega_su_dia(logged_client, user):
    tarea = Tarea(idUser=user.idUser, descripcion='Era de mañana', fecha=HOY())
    db.session.add(tarea)
    db.session.commit()
    assert logged_client.post(f'/tareas/{tarea.idTarea}/toggle').get_json()['completada'] is True


# ── Doble toque al agregar ──

def test_doble_toque_no_crea_la_tarea_dos_veces(logged_client, user):
    primera = _agregar(logged_client, 'Comprar pan').get_json()
    segunda = _agregar(logged_client, 'Comprar pan').get_json()
    assert primera['success'] and segunda['success']
    assert primera['id'] == segunda['id']
    assert Tarea.query.filter_by(idUser=user.idUser, descripcion='Comprar pan').count() == 1


def test_la_misma_tarea_otro_dia_o_mas_tarde_si_se_crea(logged_client, user):
    _agregar(logged_client, 'Leer')
    _agregar(logged_client, 'Leer', (HOY() + timedelta(days=1)).isoformat())
    assert Tarea.query.filter_by(idUser=user.idUser, descripcion='Leer').count() == 2

    # Pasado el margen del doble toque, repetirla es una tarea nueva
    vieja = Tarea.query.filter_by(idUser=user.idUser, descripcion='Leer', fecha=HOY()).one()
    vieja.createdAt = datetime.now() - timedelta(seconds=SEGUNDOS_DUPLICADO + 5)
    db.session.commit()
    _agregar(logged_client, 'Leer')
    assert Tarea.query.filter_by(idUser=user.idUser, descripcion='Leer', fecha=HOY()).count() == 2


def test_doble_toque_no_se_mezcla_entre_usuarios(logged_client, user, other_user):
    db.session.add(Tarea(idUser=other_user.idUser, descripcion='Correr', fecha=HOY()))
    db.session.commit()
    _agregar(logged_client, 'Correr')
    assert Tarea.query.filter_by(idUser=user.idUser, descripcion='Correr').count() == 1


def test_boton_agregar_se_bloquea_mientras_guarda(logged_client, user):
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert 'if (agregando) return;' in js
    assert 'addBtn.disabled = true;' in js
    assert 'addBtn.disabled = false;' in js
    # Si el servidor devuelve una tarea que ya está en pantalla, no se pinta otra vez
    assert '.tarea-item[data-id="${data.id}"]' in js


# ── Historial con cuadros por día ──

def _dia_historial(html, fecha):
    """HTML del bloque del historial de ese día (hasta el siguiente bloque o el final del panel)."""
    inicio = html.index(f'class="tareas-hist-day" data-fecha="{fecha}"')
    resto = html[inicio + 1:]
    fin = min(i for i in (resto.find('class="tareas-hist-day"'), resto.find('id="fechaSelector"')) if i != -1)
    return html[inicio:inicio + 1 + fin]


def _stat(bloque, nombre):
    return int(re.search(rf'<strong data-stat="{nombre}">(\d+)</strong>', bloque).group(1))


def test_historial_cuadros_de_un_dia_pasado(logged_client, user):
    ayer = HOY() - timedelta(days=1)
    for descripcion, hecha in (('A', True), ('B', True), ('C', False)):
        db.session.add(Tarea(idUser=user.idUser, descripcion=descripcion, fecha=ayer, completada=hecha))
    db.session.commit()
    bloque = _dia_historial(logged_client.get('/tareas/').get_data(as_text=True), ayer.isoformat())

    assert _stat(bloque, 'completadas') == 2
    assert _stat(bloque, 'no_hechas') == 1      # el día ya pasó: lo que faltó no se hizo
    assert _stat(bloque, 'pendientes') == 0
    assert _stat(bloque, 'total') == 3
    for etiqueta in ('Hechas', 'Pendientes', 'No hechas', 'Total'):
        assert f'<span>{etiqueta}</span>' in bloque


def test_historial_incluye_hoy_con_pendientes(logged_client, user):
    db.session.add(Tarea(idUser=user.idUser, descripcion='Hecha hoy', fecha=HOY(), completada=True))
    db.session.add(Tarea(idUser=user.idUser, descripcion='Falta hoy', fecha=HOY()))
    db.session.commit()
    html = logged_client.get('/tareas/').get_data(as_text=True)
    bloque = _dia_historial(html, HOY().isoformat())

    assert 'id="histHoy"' in bloque
    assert _stat(bloque, 'completadas') == 1
    assert _stat(bloque, 'pendientes') == 1     # hoy todavía hay tiempo
    assert _stat(bloque, 'no_hechas') == 0
    assert _stat(bloque, 'total') == 2
    # Hoy es la primera opción del filtro y el día que se ve al abrir
    assert re.search(rf'<option value="{HOY().isoformat()}" data-label="Hoy">', html)
    primero = re.search(r'class="tareas-hist-day" data-fecha="([\d-]+)"', html).group(1)
    assert primero == HOY().isoformat()


def test_historial_solo_muestra_las_tareas_de_su_dia(logged_client, user):
    ayer = HOY() - timedelta(days=1)
    db.session.add(Tarea(idUser=user.idUser, descripcion='Tarea de ayer', fecha=ayer))
    db.session.add(Tarea(idUser=user.idUser, descripcion='Tarea de hoy', fecha=HOY()))
    db.session.commit()
    html = logged_client.get('/tareas/').get_data(as_text=True)

    bloque_ayer = _dia_historial(html, ayer.isoformat())
    assert 'Tarea de ayer' in bloque_ayer and 'Tarea de hoy' not in bloque_ayer
    bloque_hoy = _dia_historial(html, HOY().isoformat())
    assert 'Tarea de hoy' in bloque_hoy and 'Tarea de ayer' not in bloque_hoy


def test_historial_sin_tareas_hoy_lo_dice(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    bloque = _dia_historial(html, HOY().isoformat())
    assert _stat(bloque, 'total') == 0
    assert '<p class="tareas-hist-vacio">No hay tareas este día.</p>' in bloque


def test_historial_de_hoy_se_actualiza_al_abrirlo(logged_client, user):
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert 'function refrescarHistorialHoy()' in js
    assert 'refrescarHistorialHoy();' in js


# ── Resumen general ──

def _general(html):
    inicio = html.index('id="histGeneral"')
    return html[inicio:html.index('class="tareas-hist-filter-row"', inicio)]


def test_general_suma_todas_las_tareas(logged_client, user, other_user):
    ayer = HOY() - timedelta(days=1)
    tareas = [
        (ayer, True), (ayer, False), (ayer - timedelta(days=3), False),  # pasadas: 1 hecha, 2 no
        (HOY(), True), (HOY(), False),                                    # hoy: 1 hecha, 1 pendiente
        (HOY() + timedelta(days=1), False), (HOY() + timedelta(days=9), False),  # programadas
    ]
    for i, (fecha, hecha) in enumerate(tareas):
        db.session.add(Tarea(idUser=user.idUser, descripcion=f'T{i}', fecha=fecha, completada=hecha))
    # Las de otro usuario no cuentan
    db.session.add(Tarea(idUser=other_user.idUser, descripcion='Ajena', fecha=ayer, completada=True))
    db.session.commit()

    bloque = _general(logged_client.get('/tareas/').get_data(as_text=True))
    assert _stat(bloque, 'completadas') == 2
    assert _stat(bloque, 'pendientes') == 3     # 1 de hoy + 2 programadas
    assert _stat(bloque, 'no_hechas') == 2
    assert _stat(bloque, 'total') == 7
    # Lo que JS necesita para recalcular sin recargar
    assert 'data-pasadas-hechas="1"' in bloque and 'data-pasadas-no-hechas="2"' in bloque


def test_general_sin_tareas_en_cero(logged_client, user):
    bloque = _general(logged_client.get('/tareas/').get_data(as_text=True))
    for nombre in ('completadas', 'pendientes', 'no_hechas', 'total'):
        assert _stat(bloque, nombre) == 0


def test_general_va_en_el_historial_arriba_del_filtro(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert (html.index('id="historialPanel"') < html.index('id="histGeneral"')
            < html.index('id="historialSelect"') < html.index('id="histHoy"'))
    # No sale en la página de tareas de hoy, solo al abrir el historial
    assert html.index('id="addTaskForm"') < html.index('id="histGeneral"')
    css = logged_client.get('/static/css/tareas.css').get_data(as_text=True)
    assert '.tareas-wrapper.viendo-historial #histGeneral' not in css


def test_general_se_actualiza_al_agregar_marcar_o_borrar(logged_client, user):
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert 'function refrescarGeneral()' in js
    # Al marcar, al agregar (después de pintar la tarea) y al borrar (después de quitarla)
    assert "item.classList.toggle('done', data.completada);\n                refrescarGeneral();" in js
    assert "mostrarOtraFecha();\n                refrescarGeneral();" in js
    assert js.count('refrescarGeneral();') >= 4


# ── Cada fecha elegida muestra solo sus tareas ──

def test_la_pagina_empieza_en_hoy(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert '<div class="tareas-wrapper" data-vista="hoy">' in html


def test_cada_vista_oculta_las_tareas_de_las_otras_fechas(logged_client, user):
    css = logged_client.get('/static/css/tareas.css').get_data(as_text=True)
    # Hoy: nada de mañana ni de otros días; Mañana: nada de hoy; otro día: solo ese
    for vista, selectores in (('hoy', ('#tareasList', '#tareasEmpty')),
                              ('manana', ('#proximasPanel', '#mananaEmpty')),
                              ('otra', ('#otraFechaPanel',))):
        for selector in selectores:
            assert f'.tareas-wrapper:not([data-vista="{vista}"]) {selector}' in css
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert "const vista = iso === HOY ? 'hoy' : (iso === MANANA ? 'manana' : 'otra');" in js
    assert "document.querySelector('.tareas-wrapper').dataset.vista = vista;" in js


def test_sin_tareas_para_manana_lo_dice(logged_client, user):
    _agregar(logged_client, 'Solo de hoy')
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert '<div class="tareas-empty" id="mananaEmpty">' in html
    assert 'No tienes tareas para mañana' in html


def test_con_tareas_para_manana_el_aviso_vacio_queda_oculto(logged_client, user):
    _agregar(logged_client, 'Para mañana', (HOY() + timedelta(days=1)).isoformat())
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert '<div class="tareas-empty" id="mananaEmpty" hidden>' in html
    manana = html[html.index('id="proximasPanel"'):html.index('id="otraFechaPanel"')]
    assert 'Para mañana' in manana


def test_aviso_vacio_de_manana_se_actualiza_al_agregar_o_borrar(logged_client, user):
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    assert 'mananaEmpty.hidden = hay;' in js
    assert 'mananaLista.appendChild(item);\n                actualizarProximas();' in js


def test_otro_dia_agrupa_sus_tareas_sin_mezclar(logged_client, user, other_user):
    dia_a = (HOY() + timedelta(days=4)).isoformat()
    dia_b = (HOY() + timedelta(days=20)).isoformat()
    _agregar(logged_client, 'Dentista', dia_a)
    _agregar(logged_client, 'Pagar luz', dia_a)
    _agregar(logged_client, 'Viaje', dia_b)
    db.session.add(Tarea(idUser=other_user.idUser, descripcion='Ajena lejana', fecha=HOY() + timedelta(days=4)))
    db.session.commit()
    html = logged_client.get('/tareas/').get_data(as_text=True)
    otras = html[html.index('id="otraFechaGrupos"'):html.index('id="otraFechaEmpty"')]

    grupo_a = otras[otras.index(f'data-fecha="{dia_a}"'):otras.index(f'data-fecha="{dia_b}"')]
    assert 'Dentista' in grupo_a and 'Pagar luz' in grupo_a and 'Viaje' not in grupo_a
    assert 'Viaje' in otras[otras.index(f'data-fecha="{dia_b}"'):]
    assert 'Ajena lejana' not in html
    # Hoy y mañana no se meten en los otros días
    _agregar(logged_client, 'De hoy')
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert 'De hoy' not in html[html.index('id="otraFechaPanel"'):html.index('js/tareas.js')]


def test_otro_dia_sin_tareas_lo_dice(logged_client, user):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert 'id="otraFechaEmpty"' in html
    assert 'No tienes tareas para este día' in html
    js = logged_client.get('/static/js/tareas.js').get_data(as_text=True)
    # Al agregar o borrar en otro día se vuelve a mostrar solo ese día
    assert 'function mostrarOtraFecha()' in js
    assert js.count('mostrarOtraFecha();') >= 3
