from app import db
from app.models.metodo_estudio import MetodoEstudio, KanbanTarjeta, METODOS_SUGERIDOS


def _crear_metodo(client, nombre='Pomodoro'):
    client.post('/metodos/crear', data={
        'nombre': nombre, 'descripcion': '25 min', 'icono': 'bi-stopwatch', 'color': '#ff6fb5',
    })
    return MetodoEstudio.query.filter_by(nombre=nombre).one()


def _crear_tarjeta(client, metodo, titulo='Repasar', columna='pendiente'):
    client.post(f'/metodos/{metodo.idMetodo}/tarjetas/crear', data={'titulo': titulo, 'columna': columna})
    return KanbanTarjeta.query.filter_by(titulo=titulo).one()


def test_metodos_requiere_login(client):
    assert client.get('/metodos/').status_code == 302


def test_boton_metodos_en_la_barra(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert '/metodos/' in html


def test_crear_editar_y_eliminar_metodo(logged_client):
    metodo = _crear_metodo(logged_client)
    assert metodo.icono == 'bi-stopwatch'
    assert 'Pomodoro' in logged_client.get('/metodos/').get_data(as_text=True)

    logged_client.post(f'/metodos/{metodo.idMetodo}/editar', data={
        'nombre': 'Pomodoro 50/10', 'descripcion': '', 'icono': 'bi-hack', 'color': '#000',
    })
    db.session.refresh(metodo)
    assert metodo.nombre == 'Pomodoro 50/10'
    assert metodo.icono == 'bi-book'  # un ícono no permitido se reemplaza

    _crear_tarjeta(logged_client, metodo)
    logged_client.post(f'/metodos/{metodo.idMetodo}/eliminar')
    assert MetodoEstudio.query.count() == 0
    assert KanbanTarjeta.query.count() == 0  # sus tarjetas se borran con él


def test_agregar_sugeridos_no_duplica(logged_client):
    logged_client.post('/metodos/sugeridos')
    logged_client.post('/metodos/sugeridos')
    assert MetodoEstudio.query.count() == len(METODOS_SUGERIDOS)


def test_tarjetas_kanban_crear_editar_mover_eliminar(logged_client):
    metodo = _crear_metodo(logged_client)
    tarjeta = _crear_tarjeta(logged_client, metodo, columna='pendiente')
    html = logged_client.get(f'/metodos/{metodo.idMetodo}').get_data(as_text=True)
    assert 'Repasar' in html and 'Por hacer' in html

    logged_client.post(f'/metodos/tarjetas/{tarjeta.idTarjeta}/editar',
                       data={'titulo': 'Repasar cap. 3', 'descripcion': 'Con flashcards'})
    db.session.refresh(tarjeta)
    assert tarjeta.titulo == 'Repasar cap. 3'

    resp = logged_client.post(f'/metodos/tarjetas/{tarjeta.idTarjeta}/mover',
                              json={'columna': 'hecho', 'orden': [tarjeta.idTarjeta]})
    assert resp.get_json()['conteo'] == {'pendiente': 0, 'progreso': 0, 'hecho': 1}
    db.session.refresh(tarjeta)
    assert tarjeta.columna == 'hecho'

    assert logged_client.post(f'/metodos/tarjetas/{tarjeta.idTarjeta}/mover',
                              json={'columna': 'inventada'}).status_code == 400

    logged_client.post(f'/metodos/tarjetas/{tarjeta.idTarjeta}/eliminar')
    assert KanbanTarjeta.query.count() == 0


def test_no_se_puede_tocar_metodos_de_otro_usuario(logged_client, other_user):
    ajeno = MetodoEstudio(idUser=other_user.idUser, nombre='Secreto')
    db.session.add(ajeno)
    db.session.commit()
    assert logged_client.get(f'/metodos/{ajeno.idMetodo}').status_code == 404
    assert logged_client.post(f'/metodos/{ajeno.idMetodo}/eliminar').status_code == 404
    assert MetodoEstudio.query.count() == 1


# ── Apuntes de tarjetas terminadas ──

import io
import os
import pytest
from app.models.metodo_estudio import Apunte


@pytest.fixture
def carpeta_subidas(app, tmp_path):
    # Los tests nunca escriben en instance/uploads
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    return tmp_path


def _subir(client, tarjeta, nombre='apuntes.pdf', contenido=b'%PDF-1.4 prueba'):
    return client.post(
        f'/metodos/tarjetas/{tarjeta.idTarjeta}/apuntes',
        data={'archivos': (io.BytesIO(contenido), nombre)},
        content_type='multipart/form-data',
    )


def _archivos_en(carpeta):
    return [f for _, _, archivos in os.walk(carpeta) for f in archivos]


def test_solo_se_suben_apuntes_en_hecho(logged_client, carpeta_subidas):
    metodo = _crear_metodo(logged_client)
    tarjeta = _crear_tarjeta(logged_client, metodo, columna='progreso')
    _subir(logged_client, tarjeta)
    assert Apunte.query.count() == 0
    assert _archivos_en(carpeta_subidas) == []


def test_subir_ver_y_eliminar_apunte(logged_client, carpeta_subidas):
    metodo = _crear_metodo(logged_client)
    tarjeta = _crear_tarjeta(logged_client, metodo, columna='hecho')
    _subir(logged_client, tarjeta, 'Resumen cap 3.pdf')

    apunte = Apunte.query.one()
    assert apunte.nombreOriginal == 'Resumen cap 3.pdf'
    assert apunte.nombreGuardado.endswith('.pdf') and 'Resumen' not in apunte.nombreGuardado
    assert len(_archivos_en(carpeta_subidas)) == 1

    html = logged_client.get(f'/metodos/{metodo.idMetodo}').get_data(as_text=True)
    assert 'Resumen cap 3.pdf' in html

    resp = logged_client.get(f'/metodos/apuntes/{apunte.idApunte}')
    assert resp.status_code == 200
    assert resp.data == b'%PDF-1.4 prueba'
    assert resp.headers['X-Content-Type-Options'] == 'nosniff'
    resp.close()

    logged_client.post(f'/metodos/apuntes/{apunte.idApunte}/eliminar')
    assert Apunte.query.count() == 0
    assert _archivos_en(carpeta_subidas) == []


def test_rechaza_tipos_no_permitidos(logged_client, carpeta_subidas):
    metodo = _crear_metodo(logged_client)
    tarjeta = _crear_tarjeta(logged_client, metodo, columna='hecho')
    _subir(logged_client, tarjeta, 'virus.exe', b'MZ')
    _subir(logged_client, tarjeta, 'pagina.html', b'<script>')
    assert Apunte.query.count() == 0
    assert _archivos_en(carpeta_subidas) == []


def test_borrar_tarjeta_o_metodo_borra_sus_archivos(logged_client, carpeta_subidas):
    metodo = _crear_metodo(logged_client)
    t1 = _crear_tarjeta(logged_client, metodo, 'Uno', columna='hecho')
    t2 = _crear_tarjeta(logged_client, metodo, 'Dos', columna='hecho')
    _subir(logged_client, t1, 'a.txt', b'a')
    _subir(logged_client, t2, 'b.txt', b'b')
    assert len(_archivos_en(carpeta_subidas)) == 2

    logged_client.post(f'/metodos/tarjetas/{t1.idTarjeta}/eliminar')
    assert len(_archivos_en(carpeta_subidas)) == 1

    logged_client.post(f'/metodos/{metodo.idMetodo}/eliminar')
    assert _archivos_en(carpeta_subidas) == []
    assert Apunte.query.count() == 0


def test_no_se_ven_apuntes_de_otro_usuario(logged_client, other_user, carpeta_subidas):
    ajeno_metodo = MetodoEstudio(idUser=other_user.idUser, nombre='Ajeno')
    db.session.add(ajeno_metodo)
    db.session.commit()
    ajena = KanbanTarjeta(idMetodo=ajeno_metodo.idMetodo, idUser=other_user.idUser, titulo='x', columna='hecho')
    db.session.add(ajena)
    db.session.commit()
    apunte = Apunte(idTarjeta=ajena.idTarjeta, idUser=other_user.idUser,
                    nombreOriginal='secreto.pdf', nombreGuardado='abc.pdf', tamano=1)
    db.session.add(apunte)
    db.session.commit()

    assert logged_client.get(f'/metodos/apuntes/{apunte.idApunte}').status_code == 404
    assert _subir(logged_client, ajena).status_code == 404
    assert logged_client.post(f'/metodos/apuntes/{apunte.idApunte}/eliminar').status_code == 404


def test_archivo_demasiado_grande(app, logged_client, carpeta_subidas):
    app.config['MAX_CONTENT_LENGTH'] = 1024
    metodo = _crear_metodo(logged_client)
    tarjeta = _crear_tarjeta(logged_client, metodo, columna='hecho')
    resp = _subir(logged_client, tarjeta, 'grande.pdf', b'x' * 5000)
    assert resp.status_code == 302
    assert Apunte.query.count() == 0


# ── Doble clic: no se duplican métodos ni tarjetas ──

def test_doble_envio_no_duplica_la_tarjeta(logged_client):
    metodo = _crear_metodo(logged_client)
    datos = {'titulo': 'juego de ingles', 'columna': 'pendiente'}
    for _ in range(2):
        respuesta = logged_client.post(f'/metodos/{metodo.idMetodo}/tarjetas/crear', data=datos)
        assert respuesta.status_code == 302
    assert KanbanTarjeta.query.filter_by(titulo='juego de ingles').count() == 1


def test_doble_envio_no_duplica_el_metodo(logged_client):
    _crear_metodo(logged_client)
    _crear_metodo(logged_client)  # .one() falla si quedaron dos
    assert MetodoEstudio.query.count() == 1


def test_tarjeta_con_el_mismo_titulo_pasado_el_lapso_si_se_crea(logged_client):
    from datetime import datetime
    from app.routes.metodos_route import VENTANA_DUPLICADO
    metodo = _crear_metodo(logged_client)
    primera = _crear_tarjeta(logged_client, metodo, titulo='Repasar')
    primera.createdAt = datetime.now() - VENTANA_DUPLICADO * 2
    db.session.commit()
    logged_client.post(f'/metodos/{metodo.idMetodo}/tarjetas/crear', data={'titulo': 'Repasar', 'columna': 'pendiente'})
    assert KanbanTarjeta.query.filter_by(titulo='Repasar').count() == 2


def test_mismo_titulo_en_otra_columna_si_se_crea(logged_client):
    metodo = _crear_metodo(logged_client)
    _crear_tarjeta(logged_client, metodo, titulo='Repasar', columna='pendiente')
    logged_client.post(f'/metodos/{metodo.idMetodo}/tarjetas/crear', data={'titulo': 'Repasar', 'columna': 'progreso'})
    assert KanbanTarjeta.query.filter_by(titulo='Repasar').count() == 2


def test_paginas_cargan_el_bloqueo_de_doble_envio(logged_client):
    metodo = _crear_metodo(logged_client)
    html = logged_client.get(f'/metodos/{metodo.idMetodo}').get_data(as_text=True)
    assert 'js/envio_unico.js' in html
    js = logged_client.get('/static/js/envio_unico.js').get_data(as_text=True)
    assert "dataset.enviando" in js and 'defaultPrevented' in js
