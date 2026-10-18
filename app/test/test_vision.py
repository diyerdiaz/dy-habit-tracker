import io
import os
from datetime import date, timedelta
import pytest
from app import db
from app.models.vision_board import MetaVision

from PIL import Image


def _imagen(ancho=40, alto=30, formato='PNG', orientacion=None):
    """Imagen real en memoria (Pillow) del tamaño pedido."""
    buf = io.BytesIO()
    img = Image.new('RGB', (ancho, alto), (217, 102, 255))
    if orientacion:
        exif = Image.Exif()
        exif[0x0112] = orientacion
        img.save(buf, formato, exif=exif)
    else:
        img.save(buf, formato)
    return buf.getvalue()


PNG = _imagen()
JPG = _imagen(formato='JPEG')


@pytest.fixture
def carpeta_subidas(app, tmp_path):
    # Las imágenes de los tests van a una carpeta temporal, nunca a instance/
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    return tmp_path


def _crear_meta(client, titulo='Viajar a Japón', contenido=PNG, nombre='japon.png', **extra):
    data = {'titulo': titulo, 'imagen': (io.BytesIO(contenido), nombre), **extra}
    return client.post('/vision/crear', data=data, content_type='multipart/form-data')


def _ruta_imagen(carpeta, meta):
    return os.path.join(carpeta, 'vision', str(meta.idUser), meta.imagen)


def test_vision_requiere_login(client):
    assert client.get('/vision/').status_code == 302


def test_vision_vacio(logged_client):
    html = logged_client.get('/vision/').get_data(as_text=True)
    assert 'Vision Board' in html
    assert 'Tu primera meta' in html


def test_crear_meta_con_imagen(logged_client, user, carpeta_subidas):
    _crear_meta(logged_client, descripcion='Ver el monte Fuji', categoria='viajes',
                fechaObjetivo='2027-04-01')
    meta = MetaVision.query.one()
    assert meta.idUser == user.idUser
    assert meta.titulo == 'Viajar a Japón'
    assert meta.categoria == 'viajes'
    assert meta.fechaObjetivo == date(2027, 4, 1)
    assert meta.imagen.endswith('.png') and meta.imagen != 'japon.png'
    assert os.path.exists(_ruta_imagen(carpeta_subidas, meta))
    html = logged_client.get('/vision/').get_data(as_text=True)
    assert 'Viajar a Japón' in html


def test_crear_meta_sin_imagen_falla(logged_client, carpeta_subidas):
    logged_client.post('/vision/crear', data={'titulo': 'Sin foto'})
    assert MetaVision.query.count() == 0


def test_crear_meta_sin_titulo_falla(logged_client, carpeta_subidas):
    _crear_meta(logged_client, titulo='  ')
    assert MetaVision.query.count() == 0


def test_rechaza_extension_no_permitida(logged_client, carpeta_subidas):
    _crear_meta(logged_client, contenido=b'<script>alert(1)</script>', nombre='malo.html')
    assert MetaVision.query.count() == 0


def test_rechaza_archivo_disfrazado_de_imagen(logged_client, carpeta_subidas):
    _crear_meta(logged_client, contenido=b'esto no es una imagen', nombre='falso.png')
    assert MetaVision.query.count() == 0


def test_categoria_invalida_usa_personal(logged_client, carpeta_subidas):
    _crear_meta(logged_client, categoria='hackeo')
    assert MetaVision.query.one().categoria == 'personal'


def test_ver_imagen_propia(logged_client, carpeta_subidas):
    _crear_meta(logged_client)
    meta = MetaVision.query.one()
    resp = logged_client.get(f'/vision/{meta.idMeta}/imagen')
    assert resp.status_code == 200
    assert resp.data == PNG
    assert resp.headers['X-Content-Type-Options'] == 'nosniff'


def test_no_ve_metas_de_otro_usuario(logged_client, other_user, carpeta_subidas):
    ajena = MetaVision(idUser=other_user.idUser, titulo='Meta ajena', imagen='ajena.png')
    db.session.add(ajena)
    db.session.commit()
    assert 'Meta ajena' not in logged_client.get('/vision/').get_data(as_text=True)
    assert logged_client.get(f'/vision/{ajena.idMeta}/imagen').status_code == 404
    assert logged_client.post(f'/vision/{ajena.idMeta}/eliminar').status_code == 404
    assert logged_client.post(f'/vision/{ajena.idMeta}/cumplida').status_code == 404
    assert logged_client.post(f'/vision/{ajena.idMeta}/editar', data={'titulo': 'x'}).status_code == 404
    assert db.session.get(MetaVision, ajena.idMeta).titulo == 'Meta ajena'


def test_editar_meta_sin_cambiar_imagen(logged_client, carpeta_subidas):
    _crear_meta(logged_client)
    meta = MetaVision.query.one()
    imagen = meta.imagen
    logged_client.post(f'/vision/{meta.idMeta}/editar',
                       data={'titulo': 'Viajar a Corea', 'categoria': 'viajes'})
    db.session.refresh(meta)
    assert meta.titulo == 'Viajar a Corea'
    assert meta.imagen == imagen


def test_editar_meta_cambiando_imagen_borra_la_anterior(logged_client, carpeta_subidas):
    _crear_meta(logged_client)
    meta = MetaVision.query.one()
    vieja = _ruta_imagen(carpeta_subidas, meta)
    logged_client.post(f'/vision/{meta.idMeta}/editar',
                       data={'titulo': 'Japón', 'imagen': (io.BytesIO(JPG), 'nueva.jpg')},
                       content_type='multipart/form-data')
    db.session.refresh(meta)
    assert meta.imagen.endswith('.jpg')
    assert not os.path.exists(vieja)
    assert os.path.exists(_ruta_imagen(carpeta_subidas, meta))


def test_marcar_y_desmarcar_cumplida(logged_client, carpeta_subidas):
    _crear_meta(logged_client)
    meta = MetaVision.query.one()
    logged_client.post(f'/vision/{meta.idMeta}/cumplida')
    db.session.refresh(meta)
    assert meta.cumplida and meta.fechaCumplida is not None
    assert '¡Lograda!' in logged_client.get('/vision/').get_data(as_text=True)
    logged_client.post(f'/vision/{meta.idMeta}/cumplida')
    db.session.refresh(meta)
    assert not meta.cumplida and meta.fechaCumplida is None


def test_eliminar_meta_borra_la_imagen(logged_client, carpeta_subidas):
    _crear_meta(logged_client)
    meta = MetaVision.query.one()
    ruta = _ruta_imagen(carpeta_subidas, meta)
    logged_client.post(f'/vision/{meta.idMeta}/eliminar')
    assert MetaVision.query.count() == 0
    assert not os.path.exists(ruta)


def test_filtro_por_categoria(logged_client, carpeta_subidas):
    _crear_meta(logged_client, titulo='Correr 10K', categoria='salud')
    _crear_meta(logged_client, titulo='Ahorrar', categoria='dinero')
    html = logged_client.get('/vision/?categoria=salud').get_data(as_text=True)
    assert 'alt="Correr 10K"' in html
    assert 'alt="Ahorrar"' not in html


def test_dias_restantes():
    hoy = date(2026, 10, 18)
    meta = MetaVision(titulo='x', imagen='x.png', fechaObjetivo=hoy + timedelta(days=5))
    assert meta.dias_restantes(hoy) == 5
    assert MetaVision(titulo='x', imagen='y.png').dias_restantes(hoy) is None


def test_boton_vision_board_en_la_barra(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert '/vision/' in html
    assert 'Vision Board' in html


def test_collage_titulo_al_centro_con_cuatro_o_mas_metas(logged_client, carpeta_subidas):
    html = logged_client.get('/vision/').get_data(as_text=True)
    assert 'vision-board-pocas' in html  # con pocas metas el título va arriba
    for i in range(4):
        _crear_meta(logged_client, titulo=f'Meta {i}')
    html = logged_client.get('/vision/').get_data(as_text=True)
    assert 'vision-board-pocas' not in html
    assert html.count('class="vision-etiqueta"') == 4
    assert 'data-nueva-meta' in html


def test_guarda_el_tamano_de_la_imagen(logged_client, carpeta_subidas):
    _crear_meta(logged_client, contenido=_imagen(300, 200))
    meta = MetaVision.query.one()
    assert (meta.ancho, meta.alto) == (300, 200)


def test_foto_girada_de_celular_usa_su_orientacion_real(logged_client, carpeta_subidas):
    # Guardada acostada (400x300) pero con EXIF "girar 90°": se ve vertical
    _crear_meta(logged_client, contenido=_imagen(400, 300, 'JPEG', orientacion=6), nombre='foto.jpg')
    meta = MetaVision.query.one()
    assert (meta.ancho, meta.alto) == (300, 400)
    assert meta.forma == 'alta'


def test_forma_del_recuadro_segun_la_imagen():
    assert MetaVision(ancho=600, alto=1000).forma == 'alta'
    assert MetaVision(ancho=1000, alto=400).forma == 'ancha'
    assert MetaVision(ancho=1200, alto=900).forma == 'normal'
    assert MetaVision(ancho=800, alto=800).forma == 'normal'
    assert MetaVision().forma == 'normal'  # sin medidas todavía


def test_collage_usa_la_forma_de_cada_imagen(logged_client, carpeta_subidas):
    _crear_meta(logged_client, titulo='Vertical', contenido=_imagen(30, 60))
    _crear_meta(logged_client, titulo='Panorámica', contenido=_imagen(90, 30))
    html = logged_client.get('/vision/').get_data(as_text=True)
    assert 'vision-forma-alta' in html
    assert 'vision-forma-ancha' in html


def test_imagen_danada_se_rechaza_y_no_queda_en_disco(logged_client, carpeta_subidas):
    # Empieza como PNG pero el resto está dañado: Pillow no puede abrirla
    _crear_meta(logged_client, contenido=b'\x89PNG\r\n\x1a\n' + b'\x00' * 32)
    assert MetaVision.query.count() == 0
    carpeta = carpeta_subidas / 'vision'
    assert not carpeta.exists() or not any(carpeta.rglob('*.png'))


def test_metas_viejas_sin_medidas_se_completan(logged_client, user, carpeta_subidas):
    carpeta = carpeta_subidas / 'vision' / str(user.idUser)
    carpeta.mkdir(parents=True)
    (carpeta / 'vieja.png').write_bytes(_imagen(50, 100))
    db.session.add(MetaVision(idUser=user.idUser, titulo='Vieja', imagen='vieja.png'))
    db.session.commit()
    logged_client.get('/vision/')
    meta = MetaVision.query.one()
    assert (meta.ancho, meta.alto) == (50, 100)
