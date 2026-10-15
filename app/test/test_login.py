from app.test.conftest import TEST_PASSWORD


def test_login_success(client, user):
    response = client.post('/', data={
        'nameUser': user.nameUser,
        'passwordUser': TEST_PASSWORD,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "Hábitos de Hoy".encode() in response.data


def test_login_invalid_credentials(client, user):
    response = client.post('/', data={
        'nameUser': user.nameUser,
        'passwordUser': 'clave_incorrecta',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid credentials. Please try again." in response.data


def test_password_is_stored_hashed(user):
    assert user.passwordUser != TEST_PASSWORD
    assert user.password_is_hashed()


def test_legacy_plaintext_password_is_upgraded_on_login(app, client):
    from app import db
    from app.models.users import User
    legacy = User(nameUser="viejo")
    legacy.passwordUser = "clave_vieja"   # simula un registro antiguo en texto plano
    db.session.add(legacy)
    db.session.commit()

    response = client.post('/', data={'nameUser': 'viejo', 'passwordUser': 'clave_vieja'})
    assert response.status_code == 302
    assert db.session.get(User, legacy.idUser).password_is_hashed()


def test_dashboard_requires_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302


def test_login_already_authenticated(logged_client):
    response = logged_client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert "Hábitos de Hoy".encode() in response.data
