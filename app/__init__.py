from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():

    app = Flask(__name__)    
    app.config.from_object('config.Config')
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(idUser):
        from .models.users import User
        return User.query.get(int(idUser))

    # Register blueprints
    from app.routes import (
        users_route, auth, users_route_async, habits_route, menu_route, castigos_route
    )
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(users_route.bp)
    app.register_blueprint(users_route_async.bp)
    app.register_blueprint(habits_route.bp)
    app.register_blueprint(menu_route.bp)
    app.register_blueprint(castigos_route.bp)

    @app.errorhandler(Exception)
    def handle_error(e):
        from werkzeug.exceptions import HTTPException
        print(f"An error occurred: {str(e)}")
        if isinstance(e, HTTPException):
            return {"error": str(e)}, e.code
        return {"error": str(e)}, 500

    return app