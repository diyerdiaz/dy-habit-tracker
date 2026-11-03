"""Sección Inglés (shadowing y vocabulario): blueprint propio en ingles_route.py."""
import pytest
from flask import url_for

from app.services.ingles import (
    calcular_rango, get_letras_flotantes, RANGOS_VOCABULARIO, RANGOS_DOMINIO,
)
from app.services.palabras_aleatorias import (
    palabras_aleatorias, normalizar_cantidad, PALABRAS_INGLES, MAXIMO_PALABRAS,
)
from app.models.vocabulario import Vocabulario
from app import db

PAGINAS = [
    "/menu/ingles",
    "/menu/ingles/shadowing",
    "/menu/ingles/shadowing/temporizador",
    "/menu/ingles/shadowing/calendario",
    "/menu/ingles/shadowing/registro",
    "/menu/ingles/vocabulario",
    "/menu/ingles/vocabulario/lista",
    "/menu/ingles/vocabulario/calendario",
    "/menu/ingles/vocabulario/aprender",
    "/menu/ingles/vocabulario/rango",
    "/menu/ingles/vocabulario/historial",
    "/menu/ingles/palabras-aleatorias",
]


@pytest.mark.parametrize("url", PAGINAS)
def test_paginas_de_ingles_mantienen_su_url(logged_client, url):
    assert logged_client.get(url).status_code == 200


@pytest.mark.parametrize("url", PAGINAS)
def test_paginas_de_ingles_piden_sesion(client, url):
    assert client.get(url).status_code == 302


def test_endpoints_cambian_a_blueprint_ingles(app):
    with app.test_request_context():
        assert url_for("ingles.ingles") == "/menu/ingles"
        assert url_for("ingles.vocabulario_calificar") == "/menu/ingles/vocabulario/calificar"
        assert url_for("ingles.shadowing_guardar") == "/menu/ingles/shadowing/guardar"
        assert url_for("ingles.shadowing_editar", sesion_id=3) == "/menu/ingles/shadowing/3/editar"
        assert url_for("ingles.vocabulario_eliminar", vocab_id=3) == "/menu/ingles/vocabulario/3/eliminar"
    rutas_menu = [r.endpoint for r in app.url_map.iter_rules() if r.endpoint.startswith("menu.")]
    assert not [e for e in rutas_menu if "vocabulario" in e or "shadowing" in e or e == "menu.ingles"]


def test_sidebar_enlaza_a_ingles(logged_client):
    html = logged_client.get("/dashboard").get_data(as_text=True)
    assert 'href="/menu/ingles"' in html


def test_agregar_palabra_sigue_funcionando(logged_client, user):
    respuesta = logged_client.post("/menu/ingles/vocabulario", data={
        "nombre": "Apple", "significado": "Manzana", "ejemplos": "I eat an apple",
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    assert Vocabulario.query.filter_by(idUser=user.idUser, nombre="Apple").count() == 1


def test_letras_flotantes_usan_vocabulario_del_usuario(app, user):
    with app.app_context():
        assert len(get_letras_flotantes(user.idUser)) == 10
        assert "Hello" in get_letras_flotantes(user.idUser)
        db.session.add(Vocabulario(idUser=user.idUser, nombre="Tree", significado="Árbol"))
        db.session.commit()
        assert get_letras_flotantes(user.idUser) == ["Tree"] * 10


def test_calcular_rango():
    actual, siguiente, pct, faltan = calcular_rango(0, RANGOS_VOCABULARIO)
    assert actual["nombre"] == "Novato" and siguiente["nombre"] == "Aprendiz"
    assert (pct, faltan) == (0, 25)
    actual, siguiente, pct, faltan = calcular_rango(50, RANGOS_VOCABULARIO)
    assert actual["nombre"] == "Aprendiz" and pct == 50 and faltan == 25
    actual, siguiente, pct, faltan = calcular_rango(100, RANGOS_DOMINIO)
    assert actual["nombre"] == "Dominado" and siguiente is None and (pct, faltan) == (100, 0)


def test_ingles_muestra_tarjeta_de_palabras_aleatorias(logged_client):
    html = logged_client.get("/menu/ingles").get_data(as_text=True)
    assert 'href="/menu/ingles/palabras-aleatorias"' in html
    assert "Palabras aleatorias" in html


def test_palabras_aleatorias_sin_cantidad_muestra_solo_el_formulario(logged_client):
    html = logged_client.get("/menu/ingles/palabras-aleatorias").get_data(as_text=True)
    assert 'name="cantidad"' in html
    assert "Iniciar" in html
    assert "palabras-card" not in html


def test_palabras_aleatorias_muestra_la_cantidad_pedida(logged_client):
    html = logged_client.get("/menu/ingles/palabras-aleatorias?cantidad=7").get_data(as_text=True)
    assert html.count('class="ingles-card palabras-card"') == 7
    assert "Otra tanda" in html


@pytest.mark.parametrize("valor, esperado", [("0", 1), ("-3", 1), ("500", MAXIMO_PALABRAS)])
def test_palabras_aleatorias_limita_la_cantidad(logged_client, valor, esperado):
    html = logged_client.get(f"/menu/ingles/palabras-aleatorias?cantidad={valor}").get_data(as_text=True)
    assert html.count('class="ingles-card palabras-card"') == esperado


def test_palabras_aleatorias_ignora_cantidad_no_numerica(logged_client):
    respuesta = logged_client.get("/menu/ingles/palabras-aleatorias?cantidad=abc")
    assert respuesta.status_code == 200
    assert "palabras-card" not in respuesta.get_data(as_text=True)


def test_normalizar_cantidad():
    assert normalizar_cantidad("5") == 5
    assert normalizar_cantidad(None) is None
    assert normalizar_cantidad("x") is None
    assert normalizar_cantidad("0") == 1
    assert normalizar_cantidad("999") == MAXIMO_PALABRAS


def test_palabras_aleatorias_no_se_repiten_y_vienen_de_la_lista():
    elegidas = palabras_aleatorias(MAXIMO_PALABRAS)
    nombres = [p["palabra"] for p in elegidas]
    assert len(nombres) == MAXIMO_PALABRAS == len(set(nombres))
    lista = dict(PALABRAS_INGLES)
    assert all(lista[p["palabra"]] == p["significado"] for p in elegidas)


def test_lista_de_palabras_sin_repetidas_y_suficiente():
    nombres = [palabra for palabra, _ in PALABRAS_INGLES]
    assert len(nombres) == len(set(nombres))
    assert len(nombres) >= MAXIMO_PALABRAS
