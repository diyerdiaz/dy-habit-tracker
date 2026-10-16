from app import db
from app.models.users import User
from app.test.conftest import TEST_PASSWORD


def _usuario(user):
    db.session.expire_all()
    return db.session.get(User, user.idUser)


def test_perfil_requiere_login(client):
    assert client.get('/perfil/').status_code == 302


def test_perfil_muestra_datos(logged_client, user):
    html = logged_client.get('/perfil/').get_data(as_text=True)
    assert user.nameUser in html
    assert 'Cambiar usuario' in html and 'Cambiar contraseña' in html


def test_boton_perfil_en_la_barra(logged_client):
    assert '/perfil/' in logged_client.get('/dashboard').get_data(as_text=True)


def test_cambiar_usuario(logged_client, user):
    logged_client.post('/perfil/usuario', data={'nuevo_usuario': 'nuevo_nombre', 'contrasena_actual': TEST_PASSWORD})
    assert _usuario(user).nameUser == 'nuevo_nombre'


def test_cambiar_usuario_exige_contrasena_actual(logged_client, user):
    logged_client.post('/perfil/usuario', data={'nuevo_usuario': 'otro_nombre', 'contrasena_actual': 'incorrecta'})
    assert _usuario(user).nameUser == 'test_user'


def test_no_permite_usuario_repetido(logged_client, user, other_user):
    logged_client.post('/perfil/usuario', data={'nuevo_usuario': other_user.nameUser, 'contrasena_actual': TEST_PASSWORD})
    assert _usuario(user).nameUser == 'test_user'


def test_cambiar_contrasena(logged_client, user):
    logged_client.post('/perfil/contrasena', data={
        'contrasena_actual': TEST_PASSWORD,
        'nueva_contrasena': 'clave_nueva_123',
        'confirmar_contrasena': 'clave_nueva_123',
    })
    u = _usuario(user)
    assert u.check_password('clave_nueva_123')
    assert not u.check_password(TEST_PASSWORD)


def test_contrasena_no_cambia_si_algo_falla(logged_client, user):
    casos = [
        {'contrasena_actual': 'incorrecta', 'nueva_contrasena': 'clave_nueva_123', 'confirmar_contrasena': 'clave_nueva_123'},
        {'contrasena_actual': TEST_PASSWORD, 'nueva_contrasena': 'corta', 'confirmar_contrasena': 'corta'},
        {'contrasena_actual': TEST_PASSWORD, 'nueva_contrasena': 'clave_nueva_123', 'confirmar_contrasena': 'otra_cosa_123'},
    ]
    for datos in casos:
        logged_client.post('/perfil/contrasena', data=datos)
        assert _usuario(user).check_password(TEST_PASSWORD)


def test_puede_iniciar_sesion_con_los_datos_nuevos(client, user):
    client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD})
    client.post('/perfil/usuario', data={'nuevo_usuario': 'renombrado', 'contrasena_actual': TEST_PASSWORD})
    client.post('/perfil/contrasena', data={
        'contrasena_actual': TEST_PASSWORD, 'nueva_contrasena': 'otra_clave_99', 'confirmar_contrasena': 'otra_clave_99',
    })
    client.get('/logout')
    resp = client.post('/', data={'nameUser': 'renombrado', 'passwordUser': 'otra_clave_99'})
    assert resp.status_code == 302 and '/dashboard' in resp.headers['Location']


def test_borrar_cuenta_borra_metodos_de_estudio(logged_client, user):
    from app.models.metodo_estudio import MetodoEstudio, KanbanTarjeta
    metodo = MetodoEstudio(idUser=user.idUser, nombre='Pomodoro')
    db.session.add(metodo)
    db.session.commit()
    db.session.add(KanbanTarjeta(idMetodo=metodo.idMetodo, idUser=user.idUser, titulo='x'))
    db.session.commit()

    logged_client.post(f'/User/delete/{user.idUser}')
    assert MetodoEstudio.query.count() == 0
    assert KanbanTarjeta.query.count() == 0


# ── Foto de perfil ──

import io
import os
import pytest
from PIL import Image


@pytest.fixture
def carpeta_subidas(app, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    return tmp_path


def _imagen(formato='PNG', tam=(800, 500)):
    buf = io.BytesIO()
    Image.new('RGB', tam, (138, 40, 255)).save(buf, formato)
    buf.seek(0)
    return buf


def _subir_foto(client, contenido, nombre='yo.png'):
    return client.post('/perfil/foto', data={'foto': (contenido, nombre)}, content_type='multipart/form-data')


def _fotos(carpeta):
    ruta = os.path.join(carpeta, 'avatars')
    return os.listdir(ruta) if os.path.isdir(ruta) else []


def test_subir_foto_la_recorta_cuadrada(logged_client, user, carpeta_subidas):
    _subir_foto(logged_client, _imagen())
    u = _usuario(user)
    assert u.avatar and u.avatar.endswith('.jpg')
    with Image.open(os.path.join(carpeta_subidas, 'avatars', u.avatar)) as img:
        assert img.size == (400, 400)

    resp = logged_client.get('/perfil/foto')
    assert resp.status_code == 200 and resp.mimetype == 'image/jpeg'
    resp.close()
    assert 'perfil/foto?v=' in logged_client.get('/perfil/').get_data(as_text=True)


def test_cambiar_foto_borra_la_anterior(logged_client, user, carpeta_subidas):
    _subir_foto(logged_client, _imagen())
    primera = _usuario(user).avatar
    _subir_foto(logged_client, _imagen('JPEG'), 'otra.jpg')
    assert _usuario(user).avatar != primera
    assert _fotos(carpeta_subidas) == [_usuario(user).avatar]


def test_rechaza_archivos_que_no_son_imagen(logged_client, user, carpeta_subidas):
    _subir_foto(logged_client, io.BytesIO(b'<script>alert(1)</script>'), 'falsa.png')
    _subir_foto(logged_client, _imagen(), 'foto.svg')
    assert _usuario(user).avatar is None
    assert _fotos(carpeta_subidas) == []


def test_quitar_foto(logged_client, user, carpeta_subidas):
    _subir_foto(logged_client, _imagen())
    logged_client.post('/perfil/foto/quitar')
    assert _usuario(user).avatar is None
    assert _fotos(carpeta_subidas) == []
    assert logged_client.get('/perfil/foto').status_code == 404


def test_borrar_cuenta_borra_la_foto(logged_client, user, carpeta_subidas):
    _subir_foto(logged_client, _imagen())
    logged_client.post(f'/User/delete/{user.idUser}')
    assert _fotos(carpeta_subidas) == []


def test_efecto_del_mouse_en_todas_las_paginas(client):
    assert 'js/cursor.js' in client.get('/').get_data(as_text=True)


# ── Logo, título e instalación como app ──

def test_titulo_y_logo_en_la_pestana(logged_client):
    html = logged_client.get('/tareas/').get_data(as_text=True)
    assert '<title>Tareas del Día · Habits</title>' in html
    assert 'img/logo.svg' in html and '/manifest.webmanifest' in html


def test_manifiesto_y_service_worker(client):
    m = client.get('/manifest.webmanifest')
    assert m.mimetype == 'application/manifest+json'
    datos = m.get_json(force=True)
    assert datos['name'] == 'Habits' and datos['display'] == 'standalone'
    assert any(i.get('purpose') == 'maskable' for i in datos['icons'])

    sw = client.get('/sw.js')
    assert sw.status_code == 200 and sw.headers['Service-Worker-Allowed'] == '/'
    sw.close()
    assert client.get('/offline').status_code == 200
    fav = client.get('/favicon.ico')
    assert fav.status_code == 200
    fav.close()
