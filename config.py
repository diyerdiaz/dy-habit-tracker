import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')


def _load_secret_key():
    """La clave secreta debe ser estable entre reinicios (si no, se cierran todas
    las sesiones cada vez que arranca la app). Se toma de la variable de entorno
    SECRET_KEY y, si no existe, se genera una vez y se guarda en instance/secret_key
    (esa carpeta no se versiona)."""
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    key_path = os.path.join(INSTANCE_DIR, 'secret_key')
    if os.path.exists(key_path):
        with open(key_path) as f:
            key = f.read().strip()
            if key:
                return key
    key = secrets.token_urlsafe(48)
    with open(key_path, 'w') as f:
        f.write(key)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///flaskdb.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = _load_secret_key()

    # Cookies de sesión más seguras
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    # Con HTTPS (en internet) pon SESSION_COOKIE_SECURE=1 para que la cookie
    # de sesión nunca viaje sin cifrar. En local por http debe quedar en 0.
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # Archivos de apuntes subidos (instance/ no se versiona) y tamaño máximo por petición
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(INSTANCE_DIR, 'uploads'))
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    # Protección CSRF (Flask-WTF): sin límite de tiempo para no romper pestañas abiertas
    WTF_CSRF_TIME_LIMIT = None

#Comandos para descargar en instalar todas las librerias offline  
#python -m pip download -r requirements.txt -d librerias
#pip install --no-index --find-links=librerias -r requirements.txt
