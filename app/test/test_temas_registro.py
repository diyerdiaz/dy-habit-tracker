"""Temas aleatorios: botones "Ya explicados" y "Últimas explicaciones", cada uno
con páginas de 6 y botones Anterior / Siguiente. Todo sale de la base de datos."""
import re
from datetime import datetime, timedelta

from app import db
from app.models.temas import TemaExplicar, SesionExplicacion


def _explicados(user, cantidad, prefijo='Tema'):
    """Crea temas ya explicados, cada uno con su explicación guardada. El
    primero es el más antiguo."""
    base = datetime(2026, 1, 1, 10, 0)
    temas = []
    for i in range(cantidad):
        cuando = base + timedelta(hours=i)
        tema = TemaExplicar(idUser=user.idUser, titulo=f'{prefijo} {i + 1:02d}',
                            estudiado=True, fechaEstudiado=cuando)
        db.session.add(tema)
        db.session.flush()
        db.session.add(SesionExplicacion(idTema=tema.idTema, idUser=user.idUser, segundosObjetivo=60,
                                         segundosHablados=50, calificacion=4, fecha=cuando))
        temas.append(tema)
    db.session.commit()
    return temas


def _html(logged_client, **params):
    resp = logged_client.get('/temas/', query_string=params)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def _panel(html, id_panel):
    """Contenido del panel hasta el siguiente panel (o el final de la sección)."""
    inicio = html.index(f'id="{id_panel}"')
    fin = html.find('class="temas-panel"', inicio + 1)
    fin = html.index('</section>', inicio) if fin == -1 else fin
    return html[inicio:fin]


def _titulos(panel):
    """Números de los temas que se ven en la lista (no en los avisos de borrar)."""
    return re.findall(r'class="temas-(?:item-titulo|hist-tema)">(?:<i[^>]*></i> )?Tema (\d\d)<', panel)


def test_los_dos_botones_con_sus_totales(logged_client, user):
    _explicados(user, 3)
    html = _html(logged_client)
    assert 'Ya explicados (3)' in html and 'Últimas explicaciones (3)' in html
    assert 'data-panel="panel-explicados"' in html and 'data-panel="panel-historial"' in html


def test_por_defecto_se_ve_ya_explicados(logged_client, user):
    _explicados(user, 1)
    html = _html(logged_client)
    assert re.search(r'<div[^>]*id="panel-explicados"[^>]*>', html).group(0).find('hidden') == -1
    assert 'hidden' in re.search(r'<div[^>]*id="panel-historial"[^>]*>', html).group(0)


def test_vista_historial_abre_ese_boton(logged_client, user):
    _explicados(user, 1)
    html = _html(logged_client, vista='historial')
    assert 'hidden' not in re.search(r'<div[^>]*id="panel-historial"[^>]*>', html).group(0)
    assert 'hidden' in re.search(r'<div[^>]*id="panel-explicados"[^>]*>', html).group(0)


def test_vista_desconocida_vuelve_a_explicados(logged_client, user):
    _explicados(user, 1)
    html = _html(logged_client, vista='<script>')
    assert 'hidden' not in re.search(r'<div[^>]*id="panel-explicados"[^>]*>', html).group(0)


def test_solo_6_por_pagina_del_mas_reciente_al_mas_antiguo(logged_client, user):
    _explicados(user, 14)
    html = _html(logged_client)
    assert _titulos(_panel(html, 'panel-explicados')) == ['14', '13', '12', '11', '10', '09']
    assert _titulos(_panel(html, 'panel-historial')) == ['14', '13', '12', '11', '10', '09']
    assert 'Página 1 de 3' in _panel(html, 'panel-explicados')


def test_siguiente_y_anterior(logged_client, user):
    _explicados(user, 14)
    pag1 = _panel(_html(logged_client), 'panel-explicados')
    assert 'Siguiente' in pag1 and 'Anterior' not in pag1

    pag2 = _panel(_html(logged_client, pag_explicados=2), 'panel-explicados')
    assert _titulos(pag2) == ['08', '07', '06', '05', '04', '03']
    assert 'Siguiente' in pag2 and 'Anterior' in pag2

    pag3 = _panel(_html(logged_client, pag_explicados=3), 'panel-explicados')
    assert _titulos(pag3) == ['02', '01']
    assert 'Anterior' in pag3 and 'Siguiente' not in pag3


def test_cada_boton_tiene_su_propia_pagina(logged_client, user):
    _explicados(user, 14)
    html = _html(logged_client, vista='historial', pag_historial=3, pag_explicados=2)
    assert _titulos(_panel(html, 'panel-historial')) == ['02', '01']
    assert _titulos(_panel(html, 'panel-explicados')) == ['08', '07', '06', '05', '04', '03']


def test_los_enlaces_mantienen_abierto_su_boton(logged_client, user):
    _explicados(user, 14)
    html = _html(logged_client)  # se ve "Ya explicados", pero el historial también tiene enlaces
    enlace_hist = re.search(r'href="([^"]*pag_historial=2[^"]*)"', _panel(html, 'panel-historial')).group(1)
    assert 'vista=historial' in enlace_hist and enlace_hist.endswith('#temas-registro')
    enlace_exp = re.search(r'href="([^"]*pag_explicados=2[^"]*)"', _panel(html, 'panel-explicados')).group(1)
    assert 'vista=explicados' in enlace_exp


def test_pagina_fuera_de_rango_muestra_la_ultima(logged_client, user):
    _explicados(user, 7)
    panel = _panel(_html(logged_client, pag_explicados=99), 'panel-explicados')
    assert _titulos(panel) == ['01'] and 'Página 2 de 2' in panel
    panel = _panel(_html(logged_client, pag_explicados=-4), 'panel-explicados')
    assert 'Página 1 de 2' in panel


def test_con_6_o_menos_no_hay_paginacion(logged_client, user):
    _explicados(user, 6)
    html = _html(logged_client)
    assert 'temas-paginacion' not in html.split('id="temas-registro"')[1]


def test_sin_explicaciones_muestra_mensajes(logged_client, user):
    db.session.add(TemaExplicar(idUser=user.idUser, titulo='Pendiente'))
    db.session.commit()
    html = _html(logged_client)
    assert 'Todavía no has explicado ningún tema' in html
    assert 'Aquí verás cada explicación' in html


def test_lo_que_se_ve_coincide_con_la_base_de_datos(logged_client, user):
    """Guardar una explicación de verdad aparece en los dos botones."""
    tema = TemaExplicar(idUser=user.idUser, titulo='Tema 01')
    db.session.add(tema)
    db.session.commit()
    logged_client.post('/temas/sesion', json={'tema': tema.idTema, 'objetivo': 120, 'hablados': 95, 'calificacion': 5})
    html = _html(logged_client)
    assert TemaExplicar.query.filter_by(idUser=user.idUser, estudiado=True).count() == 1
    assert SesionExplicacion.query.filter_by(idUser=user.idUser).count() == 1
    assert 'Ya explicados (1)' in html and 'Últimas explicaciones (1)' in html
    assert '1:35 / 2 min' in _panel(html, 'panel-historial')


def test_no_se_ven_temas_de_otro_usuario(logged_client, user, other_user):
    _explicados(other_user, 3, prefijo='Ajeno')
    html = _html(logged_client)
    assert 'Ajeno' not in html
    assert 'Ya explicados (0)' in html


def test_botones_con_js_sin_script_inline(logged_client, user):
    _explicados(user, 1)
    html = _html(logged_client)
    assert 'js/temas.js' in html
    assert 'temas-pestana' not in ''.join(re.findall(r'<script>(.*?)</script>', html, re.S))
