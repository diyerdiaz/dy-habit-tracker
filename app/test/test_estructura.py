"""Comprueba que cada cosa esté en su carpeta (reglas de CLAUDE.md)."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent

# offline.html lleva su CSS adentro a propósito: el service worker la guarda
# sola en caché y se muestra sin internet, cuando no se puede pedir un .css.
EXCEPCIONES_STYLE = {"offline.html"}
MAX_LINEAS_INLINE = 15


def test_rutas_siguen_convencion_de_nombre():
    for archivo in (APP / "routes").glob("*.py"):
        if archivo.name == "__init__.py":
            continue
        assert archivo.name.endswith("_route.py"), archivo.name


def test_no_hay_modelos_en_rutas_ni_rutas_en_modelos():
    for archivo in (APP / "routes").glob("*.py"):
        assert "db.Model" not in archivo.read_text(), archivo.name
    for archivo in (APP / "models").glob("*.py"):
        texto = archivo.read_text()
        assert "Blueprint" not in texto and ".route(" not in texto, archivo.name


def test_plantillas_sin_script_ni_style_largos():
    for plantilla in (APP / "templates").rglob("*.html"):
        texto = plantilla.read_text()
        for bloque in re.findall(r"<script>(.*?)</script>", texto, re.S):
            assert bloque.count("\n") <= MAX_LINEAS_INLINE, f"script largo en {plantilla}"
        if plantilla.name in EXCEPCIONES_STYLE:
            continue
        for bloque in re.findall(r"<style[^>]*>(.*?)</style>", texto, re.S):
            assert bloque.count("\n") <= MAX_LINEAS_INLINE, f"style largo en {plantilla}"


def test_perfil_y_medallas_cargan_su_js(logged_client):
    client = logged_client
    for url, js in (("/perfil/", "js/perfil.js"), ("/medallas/", "js/medallas.js")):
        respuesta = client.get(url, follow_redirects=True)
        assert respuesta.status_code == 200
        assert js in respuesta.get_data(as_text=True)
    assert client.get("/static/js/perfil.js").status_code == 200
    assert client.get("/static/js/medallas.js").status_code == 200


def test_plantillas_van_en_la_carpeta_de_su_modulo():
    # Solo el layout compartido queda suelto en templates/
    sueltas = {p.name for p in (APP / "templates").glob("*.html")}
    assert sueltas == {"base.html"}, sueltas


def test_dashboard_y_login_sin_estilos_inline_fijos():
    # Los estilos fijos van en static/css; solo se permiten los que dependen de datos ({{ }})
    for plantilla in ("dashboard/index.html", "dashboard/bienvenida.html", "auth/login.html"):
        texto = (APP / "templates" / plantilla).read_text()
        fijos = [s for s in re.findall(r'style="([^"]*)"', texto) if "{{" not in s]
        assert fijos == [], f"{plantilla}: {fijos}"


def test_login_carga_su_css(client):
    login = client.get("/").get_data(as_text=True)
    assert "css/login.css" in login and 'id="loginSection"' in login
    assert client.get("/static/css/login.css").status_code == 200


def test_dashboard_carga_su_css_sin_estilos_inline(logged_client):
    dashboard = logged_client.get("/dashboard").get_data(as_text=True)
    assert "css/dashboard.css" in dashboard
    assert 'style="margin-right: 15px' not in dashboard


def test_offline_sigue_respondiendo(client):
    respuesta = client.get("/offline")
    assert respuesta.status_code == 200
    assert "<style" in respuesta.get_data(as_text=True)


def test_menu_sin_historial_de_habitos(logged_client):
    # El historial ya se ve en Estadísticas > Calendario: se quitó del menú lateral
    for plantilla in (APP / "templates").rglob("*.html"):
        assert "url_for('menu.historial')" not in plantilla.read_text(), plantilla.name
    for url in ("/dashboard", "/register_habit", "/estadisticas/calendario"):
        html = logged_client.get(url, follow_redirects=True).get_data(as_text=True)
        assert "Historial de Hábitos" not in html, url
    assert "Calendario" in logged_client.get("/estadisticas/calendario").get_data(as_text=True)
