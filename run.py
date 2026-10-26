import os
from app import create_app
from app.services.esquema import actualizar_esquema

app = create_app()

with app.app_context():
    actualizar_esquema()

if __name__ == '__main__':
    # Por defecto: solo accesible desde este equipo y sin el depurador de Werkzeug.
    # Para desarrollar con recarga y depurador:      FLASK_DEBUG=1 python run.py
    # Para abrirla desde otro dispositivo de tu red: APP_HOST=0.0.0.0 python run.py
    #   (nunca combines ambas: el depurador permite ejecutar código en tu equipo)
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    host = os.environ.get('APP_HOST', '127.0.0.1')
    port = int(os.environ.get('APP_PORT', '5000'))
    if debug and host not in ('127.0.0.1', 'localhost'):
        print("Aviso: modo debug solo se permite en 127.0.0.1; se ignora APP_HOST.")
        host = '127.0.0.1'
    app.run(debug=debug, host=host, port=port)
