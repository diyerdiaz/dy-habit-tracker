import logging
import os
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

logger = logging.getLogger(__name__)


def actualizar_esquema():
    """Crea las tablas que falten y agrega columnas nuevas a bases de datos
    existentes (create_all no modifica tablas ya creadas). Nunca borra datos."""
    from sqlalchemy import inspect, text
    db.create_all()
    columnas_nuevas = {
        'habits': {'diasSemana': 'VARCHAR(20)'},
        'users': {'avatar': 'VARCHAR(64)'},
        'metas_vision': {'ancho': 'INTEGER', 'alto': 'INTEGER'},
        'temas_explicar': {'estudiado': 'BOOLEAN NOT NULL DEFAULT FALSE', 'fechaEstudiado': 'TIMESTAMP'},
    }
    inspector = inspect(db.engine)
    for tabla, columnas in columnas_nuevas.items():
        existentes = {c['name'] for c in inspector.get_columns(tabla)}
        for nombre, tipo in columnas.items():
            if nombre not in existentes:
                db.session.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}'))
                logger.info("Columna %s.%s agregada", tabla, nombre)
    db.session.commit()


def create_app(config_overrides=None):

    app = Flask(__name__)
    app.config.from_object('config.Config')
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(idUser):
        from .models.users import User
        return db.session.get(User, int(idUser))

    # Register blueprints
    # (se eliminó users_route_async: era una API sin autenticación que exponía
    #  contraseñas y no la usaba ninguna pantalla)
    from app.routes import (
        users_route, auth, habits_route, menu_route, castigos_route, tareas_route,
        medallas_route, motivacion_route, metodos_route, estadisticas_route,
        perfil_route, pwa_route, vision_route, temas_route,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(users_route.bp)
    app.register_blueprint(habits_route.bp)
    app.register_blueprint(menu_route.bp)
    app.register_blueprint(castigos_route.bp)
    app.register_blueprint(tareas_route.bp)
    app.register_blueprint(medallas_route.bp)
    app.register_blueprint(motivacion_route.bp)
    app.register_blueprint(metodos_route.bp)
    app.register_blueprint(estadisticas_route.bp)
    app.register_blueprint(perfil_route.bp)
    app.register_blueprint(pwa_route.bp)
    app.register_blueprint(vision_route.bp)
    app.register_blueprint(temas_route.bp)

    # Los archivos de static/ llevan ?v=<fecha de modificación> en su URL: el navegador
    # los guarda un año y, cuando cambia el archivo, cambia la URL y se descarga de nuevo.
    @app.url_defaults
    def version_de_estaticos(endpoint, values):
        if endpoint == 'static' and 'filename' in values and 'v' not in values:
            ruta = os.path.join(app.static_folder, values['filename'])
            try:
                values['v'] = int(os.stat(ruta).st_mtime)
            except OSError:
                pass

    @app.after_request
    def cache_de_estaticos(respuesta):
        if request.endpoint == 'static' and request.args.get('v') and respuesta.status_code == 200:
            respuesta.cache_control.public = True
            respuesta.cache_control.max_age = 31536000
            respuesta.cache_control.immutable = True
        return respuesta

    @app.context_processor
    def tema_de_la_app():
        from flask import session
        from app.models.personajes_login import tema_del_sitio, personaje_del_sitio
        return {
            'tema_sitio': tema_del_sitio(session.get('tema_sitio')),
            'personaje_sitio': personaje_del_sitio(session.get('tema_sitio')),
        }

    def _wants_json():
        return (request.is_json
                or request.headers.get('X-Requested-With') == 'fetch'
                or request.accept_mimetypes.best == 'application/json')

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        msg = 'La sesión del formulario expiró o no es válida. Recarga la página e inténtalo de nuevo.'
        if _wants_json():
            return jsonify({"success": False, "error": msg}), 400
        return render_template_string(
            '{% extends "base.html" %}{% block content %}'
            '<div class="container py-5 text-center"><h3>{{ msg }}</h3>'
            '<a class="btn btn-primary mt-3" href="javascript:history.back()">Volver</a></div>'
            '{% endblock %}', msg=msg), 400

    @app.errorhandler(413)
    def handle_too_large(e):
        from flask import flash, redirect
        mb = app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
        flash(f'El archivo es demasiado grande. El máximo es {mb} MB.', 'danger')
        return redirect(request.referrer or '/')

    @app.errorhandler(Exception)
    def handle_error(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return {"error": e.name}, e.code
        # El detalle técnico va al log, no al navegador
        db.session.rollback()
        logger.exception("Error no controlado en %s %s", request.method, request.path)
        return {"error": "Ocurrió un error interno. Inténtalo de nuevo."}, 500

    return app
