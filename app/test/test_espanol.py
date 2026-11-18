"""Sección Español: el mismo diseño que Inglés, solo para practicar palabras.
Usa las mismas páginas de vocabulario y juegos (blueprints registrados dos veces)
pero con sus propias palabras, repasos y partidas (columna `idioma`)."""
import os
from datetime import datetime

import pytest
from flask import url_for

from app import db
from app.models.juego_partida import JuegoPartida
from app.models.vocabulario import Vocabulario
from app.models.vocabulario_registro import VocabularioRegistro
from app.services.ingles import resumen_ingles, graficas_ingles, get_letras_flotantes

PAGINAS_ES = [
    '/menu/espanol',
    '/menu/espanol/vocabulario',
    '/menu/espanol/vocabulario/lista',
    '/menu/espanol/vocabulario/calendario',
    '/menu/espanol/vocabulario/aprender',
    '/menu/espanol/vocabulario/rango',
    '/menu/espanol/vocabulario/historial',
    '/menu/espanol/juegos/',
    '/menu/espanol/juegos/unir',
    '/menu/espanol/juegos/sopa',
    '/menu/espanol/juegos/ahorcado',
    '/menu/espanol/juegos/patos',
    '/menu/espanol/juegos/crucigrama',
    '/menu/espanol/juegos/mono',
]


def _agregar(client, seccion, nombre, significado='algo', ejemplos=''):
    resp = client.post(f'/menu/{seccion}/vocabulario',
                       data={'nombre': nombre, 'significado': significado, 'ejemplos': ejemplos})
    client.get(f'/menu/{seccion}/vocabulario')   # muestra (y consume) el aviso de "agregada"
    return resp


def _palabras(user, idioma):
    return {p.nombre for p in Vocabulario.query.filter_by(idUser=user.idUser, idioma=idioma)}


@pytest.mark.parametrize('url', PAGINAS_ES)
def test_paginas_de_espanol_abren(logged_client, url):
    assert logged_client.get(url).status_code == 200


@pytest.mark.parametrize('url', PAGINAS_ES)
def test_paginas_de_espanol_piden_sesion(client, url):
    assert client.get(url).status_code == 302


def test_endpoints_de_espanol(app):
    with app.test_request_context():
        assert url_for('vocabulario_es.index') == '/menu/espanol/vocabulario'
        assert url_for('vocabulario_es.aprender') == '/menu/espanol/vocabulario/aprender'
        assert url_for('juegos_es.resultado', juego='unir') == '/menu/espanol/juegos/unir/resultado'


# ── Cada idioma con sus propias palabras ──

def test_las_palabras_de_cada_idioma_van_por_separado(logged_client, user):
    _agregar(logged_client, 'ingles', 'Apple', 'Manzana')
    _agregar(logged_client, 'espanol', 'Efímero', 'Que dura poco')
    assert _palabras(user, 'en') == {'Apple'}
    assert _palabras(user, 'es') == {'Efímero'}
    lista_es = logged_client.get('/menu/espanol/vocabulario/lista').get_data(as_text=True)
    lista_en = logged_client.get('/menu/ingles/vocabulario/lista').get_data(as_text=True)
    assert 'Efímero' in lista_es and 'Apple' not in lista_es
    assert 'Apple' in lista_en and 'Efímero' not in lista_en


def test_la_misma_palabra_puede_estar_en_los_dos_idiomas(logged_client, user):
    _agregar(logged_client, 'ingles', 'Hola', 'Hi')
    _agregar(logged_client, 'espanol', 'Hola', 'Saludo')
    assert _palabras(user, 'en') == {'Hola'} and _palabras(user, 'es') == {'Hola'}


def test_agregar_en_espanol_vuelve_a_espanol(logged_client):
    resp = _agregar(logged_client, 'espanol', 'Ojalá')
    assert resp.headers['Location'].endswith('/menu/espanol/vocabulario')


def test_no_se_edita_ni_borra_una_palabra_de_otro_idioma(logged_client, user):
    _agregar(logged_client, 'ingles', 'Apple', 'Manzana')
    apple = Vocabulario.query.filter_by(nombre='Apple').one()
    assert logged_client.post(f'/menu/espanol/vocabulario/{apple.idVocab}/editar',
                              data={'nombre': 'X'}).status_code == 404
    assert logged_client.post(f'/menu/espanol/vocabulario/{apple.idVocab}/eliminar').status_code == 404
    assert db.session.get(Vocabulario, apple.idVocab).nombre == 'Apple'


def test_los_repasos_se_guardan_en_su_idioma(logged_client, user):
    _agregar(logged_client, 'espanol', 'Efímero')
    p = Vocabulario.query.filter_by(nombre='Efímero').one()
    r = logged_client.post('/menu/espanol/vocabulario/calificar',
                           json={'idVocab': p.idVocab, 'nombre': p.nombre, 'calificacion': 'facil'})
    assert r.get_json()['success']
    assert VocabularioRegistro.query.one().idioma == 'es'
    # El historial de Inglés no lo muestra; el de Español sí
    assert 'Efímero' not in logged_client.get('/menu/ingles/vocabulario/historial').get_data(as_text=True)
    assert 'Efímero' in logged_client.get('/menu/espanol/vocabulario/historial').get_data(as_text=True)


def test_aprender_en_espanol_solo_trae_palabras_en_espanol(logged_client, user):
    _agregar(logged_client, 'ingles', 'Apple')
    _agregar(logged_client, 'espanol', 'Efímero')
    html = logged_client.get('/menu/espanol/vocabulario/aprender').get_data(as_text=True)
    datos = html.split('window.VOCAB_PALABRAS = ', 1)[1].split(';\n', 1)[0]
    assert 'Ef\\u00edmero' in datos or 'Efímero' in datos
    assert 'Apple' not in datos


def test_autocompletar_solo_existe_en_ingles(logged_client):
    assert logged_client.post('/menu/espanol/vocabulario/autocompletar', json={'palabra': 'hola'}).status_code == 404
    html = logged_client.get('/menu/espanol/vocabulario').get_data(as_text=True)
    assert 'vocabAutocompletarBtn' not in html and 'Ej: Efímero' in html
    assert 'vocabAutocompletarBtn' in logged_client.get('/menu/ingles/vocabulario').get_data(as_text=True)


# ── Juegos ──

def _palabras_es(user, cantidad=6):
    palabras = [Vocabulario(idUser=user.idUser, idioma='es', nombre=f'Palabra{i}', significado=f'Definición {i}')
                for i in range(cantidad)]
    db.session.add_all(palabras)
    db.session.commit()
    return palabras


def test_juegos_de_espanol_usan_palabras_en_espanol(logged_client, user):
    _palabras_es(user)
    db.session.add(Vocabulario(idUser=user.idUser, idioma='en', nombre='Apple', significado='Manzana'))
    db.session.commit()
    html = logged_client.get('/menu/espanol/juegos/unir').get_data(as_text=True)
    assert 'Palabra0' in html and 'Apple' not in html
    assert 'data-voz="es-ES" data-lang="es"' in html
    assert '>Palabra</h2>' in html and '>Significado</h2>' in html
    assert 'data-resultado-url="/menu/espanol/juegos/unir/resultado"' in html


def test_la_partida_de_espanol_se_guarda_en_espanol(logged_client, user):
    ids = [p.idVocab for p in _palabras_es(user)]
    r = logged_client.post('/menu/espanol/juegos/unir/resultado', json={'ids': ids, 'errores': 1, 'segundos': 30})
    assert r.get_json()['success']
    assert JuegoPartida.query.one().idioma == 'es'


def test_no_se_juega_en_espanol_con_palabras_en_ingles(logged_client, user):
    ingles = [Vocabulario(idUser=user.idUser, idioma='en', nombre=f'W{i}', significado='x') for i in range(6)]
    db.session.add_all(ingles)
    db.session.commit()
    r = logged_client.post('/menu/espanol/juegos/unir/resultado',
                           json={'ids': [p.idVocab for p in ingles], 'errores': 0, 'segundos': 10})
    assert r.status_code == 400 and JuegoPartida.query.count() == 0


def test_juegos_en_ingles_siguen_en_ingles(logged_client, user):
    _palabras_es(user)
    db.session.add_all([Vocabulario(idUser=user.idUser, idioma='en', nombre=f'Word{i}', significado='x') for i in range(6)])
    db.session.commit()
    html = logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True)
    assert 'Palabra0' not in html and 'data-voz="en-US" data-lang="en"' in html


# ── Dashboard ──

def test_resumen_y_graficas_de_espanol_no_mezclan_ingles(app, user):
    hoy = datetime.now()
    db.session.add_all([
        Vocabulario(idUser=user.idUser, idioma='es', nombre='Efímero', significado='x', createdAt=hoy),
        Vocabulario(idUser=user.idUser, idioma='en', nombre='Apple', significado='x', createdAt=hoy),
        Vocabulario(idUser=user.idUser, idioma='en', nombre='Pear', significado='x', createdAt=hoy),
        JuegoPartida(idUser=user.idUser, idioma='en', juego='unir', parejas=6, fecha=hoy),
    ])
    db.session.commit()
    es = resumen_ingles(user.idUser, idioma='es')
    en = resumen_ingles(user.idUser)
    assert es['palabras_total'] == 1 and es['partidas_total'] == 0
    assert en['palabras_total'] == 2 and en['partidas_total'] == 1
    assert sum(graficas_ingles(user.idUser, idioma='es')['dia']['palabras']) == 1
    assert get_letras_flotantes(user.idUser, 'es').count('Efímero') >= 1


def test_dashboard_de_espanol_igual_que_ingles_sin_shadowing(logged_client):
    html = logged_client.get('/menu/espanol').get_data(as_text=True)
    assert 'Dashboard de Español' in html and 'Tu Español' in html
    assert 'ingles-stats' in html and 'id="graficaActividad"' in html
    for periodo in ('dia', 'mes', 'anio'):
        assert f'data-periodo="{periodo}"' in html
    # Español es solo para practicar palabras: sin shadowing
    contenido = html.split('id="sidebarOverlay"', 1)[1].split('inglesGraficasDatos', 1)[0]
    assert 'shadowing' not in contenido.lower()
    assert 'id="graficaShadowing"' not in html


def test_menu_de_espanol_tiene_vocabulario_y_juegos(logged_client):
    html = logged_client.get('/menu/espanol/vocabulario').get_data(as_text=True)
    menu = html.split('id="sidebar"', 1)[1].split('id="sidebarOverlay"', 1)[0]
    assert 'Inicio Español' in menu and 'href="/menu/espanol/juegos/"' in menu
    assert 'href="/menu/espanol/vocabulario" class="sidebar-link active"' in menu
    assert 'sidebar-toggle toggle-espanol' in menu
    assert 'Shadowing' not in menu and 'Registrar Hábito' not in menu


# ── Colores: mismo diseño que Inglés, pintado de rojo y dorado ──

def test_paginas_de_espanol_cargan_sus_colores_al_final(logged_client):
    for url in ('/menu/espanol', '/menu/espanol/vocabulario/lista', '/menu/espanol/juegos/'):
        html = logged_client.get(url).get_data(as_text=True)
        assert html.index('css/ingles.css') < html.index('css/espanol.css'), url


def test_paginas_de_ingles_no_cargan_los_colores_de_espanol(logged_client):
    for url in ('/menu/ingles', '/menu/ingles/vocabulario', '/menu/ingles/juegos/'):
        assert 'css/espanol.css' not in logged_client.get(url).get_data(as_text=True), url


def _sin_raiz(css):
    """El CSS sin su bloque :root (ahí sí van los azules: son la definición)."""
    if ':root {' not in css:
        return css
    i = css.index(':root {')
    return css[:i] + css[css.index('}', i) + 1:]


def test_css_compartido_usa_variables_de_color(app):
    """Si quedara un azul fijo, en Español se vería azul."""
    for hoja in ('ingles.css', 'vocabulario.css', 'juegos.css'):
        with open(os.path.join(app.static_folder, 'css', hoja), encoding='utf-8') as f:
            css = _sin_raiz(f.read()).lower()
        assert '#0d6efd' not in css and '#4dabff' not in css and '13, 110, 253' not in css, hoja


def test_ninguna_variable_de_color_se_define_con_ella_misma(app):
    """--tema-vivo: var(--tema-vivo) deja el color vacío (pasó al cambiar los azules)."""
    import re
    for hoja in ('ingles.css', 'vocabulario.css', 'juegos.css', 'espanol.css', 'shadowing.css'):
        with open(os.path.join(app.static_folder, 'css', hoja), encoding='utf-8') as f:
            css = f.read()
        for nombre, valor in re.findall(r'(--[\w-]+):\s*([^;]+);', css):
            assert f'var({nombre})' not in valor, (hoja, nombre)
    with open(os.path.join(app.static_folder, 'css', 'espanol.css'), encoding='utf-8') as f:
        espanol = f.read()
    assert '--tema-grad-1: #c60b1e' in espanol and '--tema-vivo: #ffc400' in espanol


def test_base_existente_sin_columna_idioma_queda_todo_en_ingles(app, user):
    """La base de la nube no tiene la columna: al arrancar se agrega y lo que ya
    había (palabras, repasos y partidas) queda en Inglés, sin perder nada."""
    from sqlalchemy import text
    from app.services.esquema import actualizar_esquema
    db.session.add(Vocabulario(idUser=user.idUser, nombre='Apple', significado='Manzana'))
    db.session.commit()
    for tabla in ('vocabularios', 'vocabulario_registros', 'juego_partidas'):
        db.session.execute(text(f'ALTER TABLE {tabla} DROP COLUMN idioma'))
    db.session.commit()

    actualizar_esquema()

    fila = db.session.execute(text("SELECT nombre, idioma FROM vocabularios")).one()
    assert tuple(fila) == ('Apple', 'en')
    for tabla in ('vocabulario_registros', 'juego_partidas'):
        columnas = [c[1] for c in db.session.execute(text(f'PRAGMA table_info({tabla})'))]
        assert 'idioma' in columnas, tabla


def test_fichas_de_juegos_toman_el_color_de_la_seccion(app):
    def leer(hoja):
        with open(os.path.join(app.static_folder, 'css', hoja), encoding='utf-8') as f:
            return f.read()
    juegos = leer('juegos.css').lower()
    assert 'background: #04162e' not in juegos and 'var(--juego-ficha,' in juegos
    assert '--juego-ficha: #04162e' in leer('ingles.css')
    assert '--juego-ficha: #2a0a10' in leer('espanol.css')


def test_lista_desplegable_toma_el_color_de_la_seccion(app):
    """La lista de "cuántas palabras" salía azul también en Español."""
    with open(os.path.join(app.static_folder, 'css', 'vocabulario.css'), encoding='utf-8') as f:
        css = f.read()
    assert '#002347' not in css
    assert '.glass-input option { background: var(--tema-oscuro' in css
    assert 'select.glass-input::picker(select)' in css


def test_aprender_en_espanol_dice_hora_de_practicar(logged_client):
    assert 'Hora de practicar' in logged_client.get('/menu/espanol/vocabulario/aprender').get_data(as_text=True)
    assert 'Practice Time' in logged_client.get('/menu/ingles/vocabulario/aprender').get_data(as_text=True)


# ── Rangos propios de Español ──

def test_espanol_tiene_rangos_propios_con_los_mismos_umbrales():
    from app.services.ingles import (RANGOS_VOCABULARIO, RANGOS_DOMINIO, RANGOS_VOCABULARIO_ES,
                                     RANGOS_DOMINIO_ES, rangos_vocabulario, rangos_dominio)
    assert rangos_vocabulario('es') is RANGOS_VOCABULARIO_ES and rangos_vocabulario('en') is RANGOS_VOCABULARIO
    assert rangos_dominio('es') is RANGOS_DOMINIO_ES and rangos_dominio('en') is RANGOS_DOMINIO
    for es, en in ((RANGOS_VOCABULARIO_ES, RANGOS_VOCABULARIO), (RANGOS_DOMINIO_ES, RANGOS_DOMINIO)):
        assert [r['umbral'] for r in es] == [r['umbral'] for r in en]
        assert not {r['nombre'] for r in es} & {r['nombre'] for r in en}   # ningún nombre repetido


def test_pagina_de_rango_en_espanol_usa_sus_nombres(logged_client, user):
    # Con una palabra calificada ya se ve también la escalera de dominio
    p = Vocabulario(idUser=user.idUser, idioma='es', nombre='Efímero', significado='x')
    db.session.add(p)
    db.session.commit()
    db.session.add(VocabularioRegistro(idUser=user.idUser, idioma='es', idVocab=p.idVocab,
                                       palabraNombre='Efímero', calificacion='facil'))
    db.session.commit()
    es = logged_client.get('/menu/espanol/vocabulario/rango').get_data(as_text=True)
    assert 'Pluma Naciente' in es and 'Alma de Cervantes' in es and 'Primer Borrador' in es
    assert 'color: #4dabff' not in es
    assert 'Novato' not in es and 'Políglota' not in es
    en = logged_client.get('/menu/ingles/vocabulario/rango').get_data(as_text=True)
    assert 'Novato' in en and 'Pluma Naciente' not in en


def test_dashboard_de_espanol_muestra_su_rango(logged_client, user):
    html = logged_client.get('/menu/espanol').get_data(as_text=True)
    assert 'Pluma Naciente' in html and 'Lector Curioso' in html and 'Novato' not in html


def test_boton_iniciar_no_cambia_de_color_al_presionarlo(app):
    with open(os.path.join(app.static_folder, 'css', 'vocabulario.css'), encoding='utf-8') as f:
        css = f.read()
    assert '#0080d6' not in css
    bloque = css.split('.btn-vocab-accent:active,', 1)[1].split('}', 1)[0]
    assert 'linear-gradient(135deg, var(--tema-grad-1), var(--tema-grad-2))' in bloque


def test_paginas_de_vocabulario_sin_azules_fijos(app):
    """Los íconos y la barra de rango iban con azul escrito a mano: en Español se veían azules."""
    import glob
    for ruta in glob.glob(os.path.join(app.root_path, 'templates', 'vocabulario', '*.html')):
        with open(ruta, encoding='utf-8') as f:
            html = f.read().lower()
        assert '#4dabff' not in html and '#0d6efd' not in html, ruta
