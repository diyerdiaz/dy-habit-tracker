"""Sección Inglés (shadowing y vocabulario): blueprint propio en ingles_route.py."""
import pytest
from flask import url_for

from app.services.ingles import (
    calcular_rango, get_letras_flotantes, RANGOS_VOCABULARIO, RANGOS_DOMINIO,
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
