"""Archivos para instalar la app en el celular (PWA): manifiesto, service worker,
página sin conexión y favicon."""

import json
from flask import Blueprint, current_app, render_template, send_from_directory, url_for

bp = Blueprint('pwa', __name__)


@bp.route('/manifest.webmanifest')
def manifest():
    icono = lambda nombre: url_for('static', filename=f'img/{nombre}')
    datos = {
        'name': 'Habits',
        'short_name': 'Habits',
        'description': 'Tus hábitos, estudio e inglés, gamificados.',
        'lang': 'es',
        'start_url': url_for('auth.dashboard') + '?origen=app',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'background_color': '#0a0012',
        'theme_color': '#7b2ff7',
        'icons': [
            {'src': icono('icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': icono('icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
            {'src': icono('icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return current_app.response_class(json.dumps(datos, ensure_ascii=False), mimetype='application/manifest+json')


@bp.route('/sw.js')
def service_worker():
    # Se sirve desde la raíz para que controle toda la app (no solo /static/)
    respuesta = send_from_directory(current_app.static_folder, 'js/sw.js', mimetype='application/javascript')
    respuesta.headers['Cache-Control'] = 'no-cache'
    respuesta.headers['Service-Worker-Allowed'] = '/'
    return respuesta


@bp.route('/offline')
def offline():
    return render_template('pwa/offline.html')


@bp.route('/favicon.ico')
def favicon():
    return send_from_directory(current_app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

