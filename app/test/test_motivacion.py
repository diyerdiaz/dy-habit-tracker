from datetime import date, timedelta
from app import db
from app.models.users import ROL_ADMIN
from app.services.motivacion import FRASES, RETOS, frase_del_dia, frases_anteriores, tarjeta_del_dia


def test_no_se_repite_ninguna_frase_hasta_fin_de_2027():
    inicio, fin = date(2026, 11, 2), date(2027, 12, 31)
    dias = (fin - inicio).days + 1
    vistas = {frase_del_dia(inicio + timedelta(days=i))['texto'] for i in range(dias)}
    assert len(vistas) == dias


def test_todas_las_frases_son_distintas_y_estan_completas():
    assert len({f['texto'] for f in FRASES}) == len(FRASES)
    for frase in FRASES:
        assert frase['texto'] and frase['personaje'] and frase['anime']
        assert frase['icono'].startswith('bi-')
        # El HTML las escaparía y dejarían de coincidir con el texto
        assert '"' not in frase['texto'] and "'" not in frase['texto']


def test_tarjeta_del_dia():
    dia = date(2026, 11, 2)
    tarjeta = tarjeta_del_dia(dia)
    assert tarjeta['fecha'] == '2026-11-02'
    assert tarjeta['frase'] == frase_del_dia(dia)
    assert tarjeta['reto'] in RETOS


def test_tarjeta_aparece_en_la_app_con_la_fecha_de_hoy(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    tarjeta = tarjeta_del_dia()
    assert 'id="fraseDia"' in html
    assert f'data-fecha="{tarjeta["fecha"]}"' in html
    assert tarjeta['frase']['texto'] in html
    assert f'Inspirada en {tarjeta["frase"]["personaje"]}' in html
    assert 'js/motivacion.js' in html


def test_tarjeta_no_aparece_sin_sesion(client):
    html = client.get('/').get_data(as_text=True)
    assert 'id="fraseDia"' not in html
    assert 'js/motivacion.js' not in html


def test_tarjeta_no_aparece_al_administrador(logged_client, user):
    user.rol = ROL_ADMIN
    db.session.commit()
    respuesta = logged_client.get('/admin/')
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)
    assert 'id="fraseDia"' not in html


def test_misma_frase_todo_el_dia_y_cambia_al_siguiente():
    hoy = date(2026, 10, 14)
    assert frase_del_dia(hoy) == frase_del_dia(hoy)
    assert frase_del_dia(hoy) != frase_del_dia(hoy + timedelta(days=1))


def test_recorre_todas_las_frases():
    inicio = date(2026, 1, 1)
    vistas = {frase_del_dia(inicio + timedelta(days=i))['texto'] for i in range(len(FRASES))}
    assert len(vistas) == len(FRASES)


def test_frases_anteriores():
    hoy = date(2026, 10, 14)
    anteriores = frases_anteriores(fecha=hoy)
    assert len(anteriores) == 6
    assert anteriores[0]['fecha'] == hoy - timedelta(days=1)


def test_motivacion_requiere_login(client):
    assert client.get('/motivacion/').status_code == 302


def test_motivacion_muestra_frase_del_dia(logged_client):
    html = logged_client.get('/motivacion/').get_data(as_text=True)
    frase = frase_del_dia()
    assert frase['texto'] in html
    assert frase['personaje'] in html


def test_boton_motivacion_en_la_barra(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert '/motivacion/' in html
