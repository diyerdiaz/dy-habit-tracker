import pytest
from app import create_app, db
from app.models.users import User


@pytest.fixture
def csrf_client():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
        # CSRF ACTIVADO en estos tests
    })
    with app.app_context():
        db.create_all()
        db.session.add(User(nameUser="u", password="clave123"))
        db.session.commit()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_post_without_csrf_token_is_rejected(csrf_client):
    response = csrf_client.post('/', data={'nameUser': 'u', 'passwordUser': 'clave123'})
    assert response.status_code == 400


def test_pages_include_csrf_token(csrf_client):
    response = csrf_client.get('/')
    assert b'name="csrf-token"' in response.data
    assert b'js/csrf.js' in response.data


def test_toggle_twice_quickly_does_not_crash(app, logged_client, user):
    from app.models.habitos import Habit
    h = Habit(idUser=user.idUser, habitName='h', habitFreq='Diaria', habitCategory='salud')
    db.session.add(h)
    db.session.commit()
    r1 = logged_client.post(f'/habit/{h.idHabit}/toggle_today')
    assert r1.status_code == 200 and r1.get_json()['done'] is True
    r2 = logged_client.post(f'/habit/{h.idHabit}/toggle_today')
    assert r2.status_code == 200 and r2.get_json()['done'] is False


def test_habit_name_is_escaped_in_onclick(logged_client, user):
    payload = "x');alert(1);//<b>"
    logged_client.post('/register_habit', data={
        'habitName': payload, 'habitFreq': 'Diaria', 'habitCategory': 'salud'})
    html = logged_client.get('/register_habit').data.decode()
    assert "x');alert(1)" not in html
    assert "<b>" not in html


def test_datos_delicados_no_se_suben_a_git():
    import subprocess
    with open('.gitignore') as f:
        reglas = f.read().split()
    assert 'instance/' in reglas and '*.sqlite' in reglas and '*.sqlite.bak*' in reglas
    rastreados = subprocess.run(['git', 'ls-files'], capture_output=True, text=True).stdout.split()
    assert not [r for r in rastreados if r.startswith('instance/') or '.sqlite' in r or r.endswith('secret_key')]


def test_datos_delicados_no_entran_a_la_imagen_docker():
    with open('.dockerignore') as f:
        reglas = f.read().split()
    assert 'instance/' in reglas and '*.sqlite' in reglas


def test_paginas_nuevas_piden_iniciar_sesion(client):
    for metodo, url in [('get', '/habitos/plan-mes'), ('post', '/habitos/plan-mes'),
                        ('get', '/habitos/recuperar'), ('post', '/habit/1/recuperar'),
                        ('post', '/habit/1/sesion_recuperacion')]:
        resp = getattr(client, metodo)(url)
        assert resp.status_code == 302 and '/?next=' in resp.headers['Location'] or resp.status_code == 401, url
