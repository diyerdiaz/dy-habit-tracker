import os

STATIC = os.path.join('app', 'static')


def test_estaticos_llevan_version_en_la_url(client):
    html = client.get('/').get_data(as_text=True)
    assert '/static/css/m.css?v=' in html
    assert '/static/js/login.js?v=' in html


def test_estaticos_con_version_se_guardan_un_anio(client):
    html = client.get('/').get_data(as_text=True)
    url = html.split('href="/static/css/m.css?v=')[1].split('"')[0]
    resp = client.get(f'/static/css/m.css?v={url}')
    assert resp.status_code == 200
    assert 'max-age=31536000' in resp.headers['Cache-Control']
    assert 'immutable' in resp.headers['Cache-Control']


def test_estaticos_sin_version_no_se_guardan_un_anio(client):
    resp = client.get('/static/css/m.css')
    assert 'max-age=31536000' not in resp.headers.get('Cache-Control', '')


def test_service_worker_sigue_sin_cache(client):
    assert client.get('/sw.js').headers['Cache-Control'] == 'no-cache'


def test_chartjs_solo_en_paginas_con_graficas(logged_client, user):
    chart = 'chart.js@4.5.1/dist/chart.umd.min.js'
    assert chart in logged_client.get('/dashboard').get_data(as_text=True)
    assert chart in logged_client.get('/menu/estadisticas').get_data(as_text=True)
    for pagina in ['/register_habit', '/habitos/check', '/habitos/recuperar', '/perfil/']:
        html = logged_client.get(pagina).get_data(as_text=True)
        assert 'chart.js' not in html, pagina


def test_iconos_pesan_poco():
    for nombre in ['icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png']:
        assert os.path.getsize(os.path.join(STATIC, 'img', nombre)) < 200_000, nombre


def test_no_queda_codigo_de_flutter(client):
    assert not os.path.exists('app_movil')
    assert client.get('/descargar/android').status_code == 404
