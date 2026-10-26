from datetime import date, timedelta
from app.services.motivacion import FRASES, frase_del_dia, frases_anteriores


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
