"""Comprueba que cada cosa esté en su carpeta (reglas de CLAUDE.md)."""
import ast
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


def test_app_solo_tiene_init_suelto():
    # La lógica que no es modelo ni ruta va en app/services/
    sueltos = {p.name for p in APP.glob("*.py")}
    assert sueltos == {"__init__.py"}, sueltos


def test_services_sin_modelos_ni_rutas():
    for archivo in (APP / "services").glob("*.py"):
        texto = archivo.read_text()
        assert "db.Model" not in texto, archivo.name
        assert "Blueprint(" not in texto and ".route(" not in texto, archivo.name


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


def test_github_actions_corre_todos_los_tests():
    flujo = (APP.parent / ".github" / "workflows" / "python-tests.yml").read_text()
    assert "pull_request:" in flujo and "push:" in flujo
    assert "pip install -r requirements.txt pytest" in flujo
    assert "pytest app/test" in flujo
    # Misma versión de Python que el Dockerfile de producción
    version = re.search(r'FROM python:(\d+\.\d+)', (APP.parent / "Dockerfile").read_text()).group(1)
    assert f'python-version: "{version}"' in flujo


def test_animacion_de_carga_en_todas_las_paginas(client, logged_client):
    for cliente, url in ((client, "/"), (logged_client, "/dashboard"), (logged_client, "/metodos/")):
        html = cliente.get(url, follow_redirects=True).get_data(as_text=True)
        # cargando.js define los puntos que luego usa envio_unico.js en los botones
        assert "js/cargando.js" in html and "js/envio_unico.js" in html, url
        assert html.index("js/cargando.js") < html.index("js/envio_unico.js"), url
    js = client.get("/static/js/cargando.js").get_data(as_text=True)
    assert "window.puntosCargando" in js and "pageshow" in js
    # Las descargas y los modales no muestran la capa (la página no cambia)
    assert "download" in js and "data-bs-toggle" in js
    css = client.get("/static/css/m.css").get_data(as_text=True)
    assert "@keyframes ola-puntos" in css and ".capa-cargando.visible" in css


def test_models_solo_tiene_modelos():
    # Un archivo en models/ define al menos un modelo; la lógica suelta va en services/
    for archivo in (APP / "models").glob("*.py"):
        if archivo.name == "__init__.py":
            continue
        assert "db.Model" in archivo.read_text(), f"{archivo.name} no tiene modelos: va en services/"


def test_rutas_no_importan_de_otras_rutas():
    # Lo que usan dos blueprints a la vez va en services/, no en otro *_route.py
    for archivo in (APP / "routes").glob("*.py"):
        assert not re.search(r"from app\.routes\.\w+ import", archivo.read_text()), archivo.name


def test_rutas_importan_todo_arriba():
    # Nada de imports a mitad de archivo después de las rutas
    for archivo in (APP / "routes").glob("*.py"):
        lineas = archivo.read_text().splitlines()
        primera_ruta = next((i for i, l in enumerate(lineas) if l.startswith(("@bp.", "def "))), len(lineas))
        tardios = [l for l in lineas[primera_ruta:] if l.startswith(("import ", "from "))]
        assert tardios == [], f"{archivo.name}: {tardios}"


def test_sin_html_escrito_en_python():
    # El HTML va en templates/, no en cadenas dentro de .py
    for archivo in APP.rglob("*.py"):
        if "test" in archivo.parts:
            continue
        assert "render_template_string" not in archivo.read_text(), archivo


def test_cada_ruta_usa_plantillas_de_su_carpeta():
    carpetas = {"ingles_route.py": "ingles/", "juegos_route.py": "juegos/", "menu_route.py": "menu/"}
    for nombre, carpeta in carpetas.items():
        texto = (APP / "routes" / nombre).read_text()
        plantillas = re.findall(r"render_template\(\s*'([^']+)'", texto)
        assert plantillas, nombre
        assert all(p.startswith(carpeta) for p in plantillas), f"{nombre}: {plantillas}"


def test_menu_ya_no_tiene_rutas_de_ingles():
    texto = (APP / "routes" / "menu_route.py").read_text()
    assert "/ingles" not in texto
    assert not list((APP / "templates" / "menu").glob("vocabulario*.html"))
    assert not list((APP / "templates" / "menu").glob("shadowing*.html"))


def test_error_csrf_usa_su_plantilla(app, logged_client):
    assert (APP / "templates" / "errores" / "csrf.html").exists()
    app.config["WTF_CSRF_ENABLED"] = True
    respuesta = logged_client.post("/menu/ingles/shadowing/guardar", data={})
    assert respuesta.status_code == 400
    html = respuesta.get_data(as_text=True)
    assert "La sesión del formulario expiró" in html and "Volver" in html


def test_actualizar_esquema_vive_en_services(app):
    import app as paquete
    from app.services.esquema import actualizar_esquema
    assert not hasattr(paquete, "actualizar_esquema")
    with app.app_context():
        actualizar_esquema()  # en una base ya creada no falla ni borra nada


def test_borrar_archivos_de_usuario_desde_services(app, tmp_path):
    from types import SimpleNamespace
    from app.services.archivos import carpeta_apuntes, borrar_apuntes, carpeta_avatars, borrar_foto
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    with app.app_context():
        carpeta = tmp_path / "apuntes" / "7"
        carpeta.mkdir(parents=True)
        (carpeta / "a.pdf").write_text("x")
        assert carpeta_apuntes(7) == str(carpeta)
        borrar_apuntes([SimpleNamespace(idUser=7, nombreGuardado="a.pdf"),
                        SimpleNamespace(idUser=7, nombreGuardado="no-existe.pdf")])
        assert not (carpeta / "a.pdf").exists()

        (tmp_path / "avatars").mkdir()
        (tmp_path / "avatars" / "f.jpg").write_text("x")
        usuario = SimpleNamespace(avatar="f.jpg")
        borrar_foto(usuario)
        assert usuario.avatar is None and not (tmp_path / "avatars" / "f.jpg").exists()
        assert carpeta_avatars() == str(tmp_path / "avatars")


def test_habitos_usa_plantillas_de_su_carpeta():
    # Las plantillas del blueprint de hábitos van en templates/habits/ (antes en register/)
    assert not (APP / "templates" / "register").exists()
    texto = (APP / "routes" / "habits_route.py").read_text()
    plantillas = re.findall(r"render_template\(\s*[\"']([^\"']+)", texto)
    assert plantillas and all(p.startswith("habits/") for p in plantillas), plantillas


def _imports_dentro_de_funciones(archivo):
    arbol = ast.parse(archivo.read_text())
    return [f"línea {n.lineno}" for f in ast.walk(arbol)
            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
            for n in ast.walk(f) if isinstance(n, (ast.Import, ast.ImportFrom))]


def test_imports_arriba_en_routes_models_y_services():
    # Nada de imports dentro de funciones: van arriba del archivo
    for carpeta in ("routes", "models", "services"):
        for archivo in (APP / carpeta).glob("*.py"):
            assert _imports_dentro_de_funciones(archivo) == [], f"{carpeta}/{archivo.name}"
