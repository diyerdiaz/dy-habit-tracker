"""Sección Inglés (shadowing y vocabulario): blueprint propio en ingles_route.py."""
import os

import pytest
from flask import url_for

from app.services.ingles import (
    calcular_rango, get_letras_flotantes, RANGOS_VOCABULARIO, RANGOS_DOMINIO,
)
from app.services.palabras_aleatorias import (
    palabras_aleatorias, normalizar_cantidad, total_vocabulario, MAXIMO_PALABRAS,
)
from app.models.vocabulario import Vocabulario
from app.models.shadowing_sesion import ShadowingSesion
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


def test_letras_flotantes_salen_al_azar_de_todo_el_vocabulario(app, user, other_user):
    for k in range(30):
        db.session.add(Vocabulario(idUser=user.idUser, nombre=f"word{k}", significado="x"))
    db.session.add(Vocabulario(idUser=other_user.idUser, nombre="ajena", significado="x"))
    db.session.commit()
    vistas = set()
    for _ in range(20):
        letras = get_letras_flotantes(user.idUser)
        assert len(letras) == 10 == len(set(letras))
        assert "ajena" not in letras
        vistas.update(letras)
    # No son siempre las 10 primeras: aparecen palabras de más adelante
    assert len(vistas) > 10 and vistas - {f"word{k}" for k in range(10)}


def test_letras_flotantes_con_pocas_palabras_las_repite(app, user):
    for nombre in ("Tree", "Sky", "Sun"):
        db.session.add(Vocabulario(idUser=user.idUser, nombre=nombre, significado="x"))
    db.session.commit()
    letras = get_letras_flotantes(user.idUser)
    assert len(letras) == 10 and set(letras) == {"Tree", "Sky", "Sun"}


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


def _agregar_vocabulario(usuario, cantidad):
    for k in range(cantidad):
        db.session.add(Vocabulario(idUser=usuario.idUser, nombre=f"word{k}", significado=f"palabra{k}"))
    db.session.commit()


def test_palabras_aleatorias_sin_cantidad_muestra_solo_el_formulario(logged_client, user):
    _agregar_vocabulario(user, 3)
    html = logged_client.get("/menu/ingles/palabras-aleatorias").get_data(as_text=True)
    assert 'name="cantidad"' in html
    assert "Iniciar" in html
    assert "palabras-card" not in html
    assert "Tienes 3 palabras en tu vocabulario" in html


def test_palabras_aleatorias_muestra_la_cantidad_pedida(logged_client, user):
    _agregar_vocabulario(user, 10)
    html = logged_client.get("/menu/ingles/palabras-aleatorias?cantidad=7").get_data(as_text=True)
    assert html.count('class="ingles-card palabras-card"') == 7
    assert "Otra tanda" in html
    assert "solo tienes" not in html


@pytest.mark.parametrize("valor, esperado", [("0", 1), ("-3", 1), ("500", MAXIMO_PALABRAS)])
def test_palabras_aleatorias_limita_la_cantidad(logged_client, user, valor, esperado):
    _agregar_vocabulario(user, MAXIMO_PALABRAS + 5)
    html = logged_client.get(f"/menu/ingles/palabras-aleatorias?cantidad={valor}").get_data(as_text=True)
    assert html.count('class="ingles-card palabras-card"') == esperado


def test_palabras_aleatorias_ignora_cantidad_no_numerica(logged_client, user):
    _agregar_vocabulario(user, 3)
    respuesta = logged_client.get("/menu/ingles/palabras-aleatorias?cantidad=abc")
    assert respuesta.status_code == 200
    assert "palabras-card" not in respuesta.get_data(as_text=True)


def test_palabras_aleatorias_salen_del_vocabulario_del_usuario(logged_client, user):
    db.session.add(Vocabulario(idUser=user.idUser, nombre="Overwhelmed", significado="Abrumado"))
    db.session.commit()
    html = logged_client.get("/menu/ingles/palabras-aleatorias?cantidad=1").get_data(as_text=True)
    assert "Overwhelmed" in html and "Abrumado" in html


def test_palabras_aleatorias_con_menos_vocabulario_que_lo_pedido(logged_client, user):
    _agregar_vocabulario(user, 2)
    html = logged_client.get("/menu/ingles/palabras-aleatorias?cantidad=5").get_data(as_text=True)
    assert html.count('class="ingles-card palabras-card"') == 2
    assert "Pediste 5, pero solo tienes 2" in html


def test_palabras_aleatorias_sin_vocabulario_invita_a_agregar(logged_client):
    html = logged_client.get("/menu/ingles/palabras-aleatorias?cantidad=5").get_data(as_text=True)
    assert "Tu vocabulario está vacío" in html
    assert 'href="/menu/ingles/vocabulario"' in html
    assert "palabras-card" not in html and 'name="cantidad"' not in html


def test_normalizar_cantidad():
    assert normalizar_cantidad("5") == 5
    assert normalizar_cantidad(None) is None
    assert normalizar_cantidad("x") is None
    assert normalizar_cantidad("0") == 1
    assert normalizar_cantidad("999") == MAXIMO_PALABRAS


def test_palabras_aleatorias_no_se_repiten_y_vienen_del_vocabulario(user, other_user):
    _agregar_vocabulario(user, 6)
    db.session.add(Vocabulario(idUser=user.idUser, nombre=" WORD0 ", significado="repetida"))
    db.session.add(Vocabulario(idUser=other_user.idUser, nombre="ajena", significado="de otro"))
    db.session.commit()
    elegidas = palabras_aleatorias(user.idUser, MAXIMO_PALABRAS)
    nombres = [p["palabra"].strip().lower() for p in elegidas]
    assert len(nombres) == 6 == len(set(nombres))
    assert "ajena" not in nombres
    assert total_vocabulario(user.idUser) == 6
    assert total_vocabulario(other_user.idUser) == 1


def test_palabras_aleatorias_sin_vocabulario_devuelve_vacio(user):
    assert palabras_aleatorias(user.idUser, 5) == []
    assert total_vocabulario(user.idUser) == 0


def test_temporizador_de_shadowing_es_circular(logged_client):
    html = logged_client.get("/menu/ingles/shadowing/temporizador").get_data(as_text=True)
    assert 'id="shadowReloj"' in html
    assert 'id="shadowRelojAvance"' in html
    assert 'id="shadowTimerDisplay"' in html
    # El reloj de arena anterior ya no se usa
    assert "shadow-hourglass" not in html


def test_temporizador_tiene_cuenta_regresiva(logged_client):
    html = logged_client.get("/menu/ingles/shadowing/temporizador").get_data(as_text=True)
    assert 'data-mode="regresiva"' in html
    assert 'id="shadowCuentaMinutos"' in html
    for minutos in (5, 10, 15, 20, 30):
        assert f'data-minutos="{minutos}"' in html
    # Aviso con el botón para apagar la alarma, oculto hasta que termine
    assert 'id="shadowAlarmaAviso" hidden' in html
    assert 'id="shadowAlarmaBtn"' in html


def test_cuenta_regresiva_completa_se_guarda(logged_client, user):
    # 20 minutos de cuenta regresiva terminada: el JS guarda 1200 segundos
    respuesta = logged_client.post("/menu/ingles/shadowing/guardar", json={"segundos": 20 * 60})
    assert respuesta.status_code == 200
    sesion = ShadowingSesion.query.filter_by(idUser=user.idUser).one()
    assert sesion.duracionSegundos == 1200
    html = logged_client.get("/menu/ingles/shadowing/temporizador").get_data(as_text=True)
    assert "20m 0s" in html


def test_campo_otro_minutos_sin_flechas(app):
    # Las flechas del input number tapaban el número en "Otro"
    ruta = os.path.join(app.static_folder, "css", "shadowing.css")
    with open(ruta, encoding="utf-8") as f:
        css = f.read()
    assert ".shadow-cuenta-otro input::-webkit-inner-spin-button" in css
    assert "appearance: textfield" in css


def test_temporizador_no_muestra_ultimas_sesiones(logged_client, user):
    db.session.add(ShadowingSesion(idUser=user.idUser, duracionSegundos=125))
    db.session.commit()
    html = logged_client.get("/menu/ingles/shadowing/temporizador").get_data(as_text=True)
    assert "Últimas sesiones" not in html
    assert "vocab-history-table" not in html
    # Los totales de arriba siguen contando la sesión
    assert "2m 5s" in html
