import random
from app import db
from app.models.temas import TemaExplicar, SesionExplicacion, TEMAS_SUGERIDOS, elegir_tema


def _crear_tema(user, titulo='Cómo funciona internet', veces=0):
    tema = TemaExplicar(idUser=user.idUser, titulo=titulo, vecesSalido=veces)
    db.session.add(tema)
    db.session.commit()
    return tema


def test_temas_requiere_login(client):
    assert client.get('/temas/').status_code == 302


def test_pagina_vacia_ofrece_sugeridos(logged_client):
    html = logged_client.get('/temas/').get_data(as_text=True)
    assert 'Temas Aleatorios' in html
    assert 'Agregar temas sugeridos' in html


def test_agregar_varios_temas_uno_por_linea(logged_client, user):
    logged_client.post('/temas/crear', data={'titulos': 'Volcanes\n  La luna  \n\nvolcanes\nMi meta'})
    titulos = sorted(t.titulo for t in TemaExplicar.query.filter_by(idUser=user.idUser))
    # sin vacíos, sin espacios sobrantes y sin repetidos (aunque cambien las mayúsculas)
    assert titulos == ['La luna', 'Mi meta', 'Volcanes']


def test_agregar_sugeridos_no_duplica(logged_client, user):
    logged_client.post('/temas/sugeridos')
    logged_client.post('/temas/sugeridos')
    assert TemaExplicar.query.filter_by(idUser=user.idUser).count() == len(TEMAS_SUGERIDOS)


def test_girar_sin_temas_da_error(logged_client):
    resp = logged_client.post('/temas/girar')
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False


def test_girar_saca_un_tema_y_lo_cuenta(logged_client, user):
    tema = _crear_tema(user)
    data = logged_client.post('/temas/girar').get_json()
    assert data['success'] and data['tema']['id'] == tema.idTema
    assert data['opciones'] == [tema.titulo]
    db.session.refresh(tema)
    assert tema.vecesSalido == 1 and tema.ultimaVez is not None


def test_girar_no_repite_el_anterior(logged_client, user):
    _crear_tema(user, 'Uno')
    _crear_tema(user, 'Dos')
    anterior = None
    for _ in range(10):
        actual = logged_client.post('/temas/girar').get_json()['tema']['id']
        assert actual != anterior
        anterior = actual


def test_elegir_tema_prefiere_los_que_menos_han_salido(app, user):
    poco = _crear_tema(user, 'Poco', veces=0)
    mucho = _crear_tema(user, 'Mucho', veces=9)
    azar = random.Random(1)
    salidas = [elegir_tema([poco, mucho], azar=azar).idTema for _ in range(400)]
    assert salidas.count(poco.idTema) > salidas.count(mucho.idTema)
    assert elegir_tema([]) is None
    assert elegir_tema([poco], anterior_id=poco.idTema) is poco  # si solo hay uno, sale ese


def test_guardar_sesion(logged_client, user):
    tema = _crear_tema(user)
    resp = logged_client.post('/temas/sesion', json={'tema': tema.idTema, 'objetivo': 120, 'hablados': 95, 'calificacion': 4})
    assert resp.get_json()['success']
    sesion = SesionExplicacion.query.one()
    assert (sesion.segundosObjetivo, sesion.segundosHablados, sesion.calificacion) == (120, 95, 4)
    assert sesion.tiempo_texto() == '1:35'
    html = logged_client.get('/temas/').get_data(as_text=True)
    assert 'Últimas explicaciones' in html


def test_guardar_sesion_valida_los_datos(logged_client, user):
    tema = _crear_tema(user)
    for malo in [{'objetivo': 0, 'hablados': 10}, {'objetivo': 99999, 'hablados': 10},
                 {'objetivo': 60, 'hablados': -1}, {'objetivo': 'x', 'hablados': 10}]:
        resp = logged_client.post('/temas/sesion', json={'tema': tema.idTema, **malo})
        assert resp.status_code == 400
    # una calificación fuera de 1-5 se guarda vacía
    logged_client.post('/temas/sesion', json={'tema': tema.idTema, 'objetivo': 60, 'hablados': 60, 'calificacion': 9})
    assert SesionExplicacion.query.one().calificacion is None


def test_no_se_tocan_temas_de_otro_usuario(logged_client, other_user):
    ajeno = _crear_tema(other_user, 'Tema ajeno')
    assert 'Tema ajeno' not in logged_client.get('/temas/').get_data(as_text=True)
    assert logged_client.post(f'/temas/{ajeno.idTema}/eliminar').status_code == 404
    assert logged_client.post(f'/temas/{ajeno.idTema}/editar', data={'titulo': 'x'}).status_code == 404
    resp = logged_client.post('/temas/sesion', json={'tema': ajeno.idTema, 'objetivo': 60, 'hablados': 30})
    assert resp.status_code == 404
    assert logged_client.post('/temas/girar').status_code == 400  # el tema ajeno no cuenta


def test_editar_y_eliminar_tema(logged_client, user):
    tema = _crear_tema(user)
    logged_client.post(f'/temas/{tema.idTema}/editar', data={'titulo': 'Internet', 'notas': 'cables y routers'})
    db.session.refresh(tema)
    assert (tema.titulo, tema.notas) == ('Internet', 'cables y routers')
    logged_client.post('/temas/sesion', json={'tema': tema.idTema, 'objetivo': 60, 'hablados': 30})
    logged_client.post(f'/temas/{tema.idTema}/eliminar')
    assert TemaExplicar.query.count() == 0
    assert SesionExplicacion.query.count() == 0  # sus sesiones se borran con él


def test_boton_temas_en_el_menu(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert '/temas/' in html and 'Temas Aleatorios' in html


def test_tablas_con_texto_blanco(client):
    # las tablas .custom-table (Gestión de Hábitos, Castigos) no deben usar el texto oscuro de Bootstrap
    css = client.get('/static/css/m.css').get_data(as_text=True)
    assert '--bs-table-color: #fff' in css


def test_tema_explicado_desaparece_de_la_lista_y_la_ruleta(logged_client, user):
    explicado = _crear_tema(user, 'Volcanes')
    otro = _crear_tema(user, 'La luna')
    logged_client.post('/temas/sesion', json={'tema': explicado.idTema, 'objetivo': 60, 'hablados': 50})
    db.session.refresh(explicado)
    assert explicado.estudiado and explicado.fechaEstudiado is not None
    for _ in range(8):  # ya nunca sale en la ruleta
        assert logged_client.post('/temas/girar').get_json()['tema']['id'] == otro.idTema
    html = logged_client.get('/temas/').get_data(as_text=True)
    assert 'Ya explicados (1)' in html
    assert 'Ya salió de tu lista' in html  # aviso al guardar


def test_sin_temas_pendientes_la_ruleta_avisa(logged_client, user):
    tema = _crear_tema(user)
    logged_client.post('/temas/sesion', json={'tema': tema.idTema, 'objetivo': 60, 'hablados': 50})
    resp = logged_client.post('/temas/girar')
    assert resp.status_code == 400 and 'No te quedan temas' in resp.get_json()['error']
    assert 'Ya explicaste todos tus temas' in logged_client.get('/temas/').get_data(as_text=True)


def test_volver_a_poner_un_tema_explicado(logged_client, user):
    tema = _crear_tema(user, 'Volcanes')
    logged_client.post('/temas/sesion', json={'tema': tema.idTema, 'objetivo': 60, 'hablados': 50})
    logged_client.post(f'/temas/{tema.idTema}/restaurar')
    db.session.refresh(tema)
    assert not tema.estudiado
    # escribirlo otra vez en "agregar" también lo devuelve, sin duplicarlo
    logged_client.post('/temas/sesion', json={'tema': tema.idTema, 'objetivo': 60, 'hablados': 50})
    logged_client.post('/temas/crear', data={'titulos': 'volcanes'})
    db.session.refresh(tema)
    assert not tema.estudiado
    assert TemaExplicar.query.count() == 1
    assert SesionExplicacion.query.count() == 2  # el historial se conserva


def test_avisos_y_login_sin_romper_otras_paginas(client):
    css = client.get('/static/css/m.css').get_data(as_text=True)
    assert '.flash-message.alert {' in css  # avisos con el color del tema
    # la cuadrícula de dos mitades es solo del login (Gestión de Hábitos usa .login-wrapper)
    assert '.login-wrapper.login-portada {' in css
    assert 'login-portada' in client.get('/').get_data(as_text=True)
