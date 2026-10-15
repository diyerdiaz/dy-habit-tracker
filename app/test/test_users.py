from app import db
from app.models.users import User


def test_register_user(client):
    response = client.post('/User/add', data={
        'nameUser': 'new_user',
        'passwordUser': 'new_password',
    })
    assert response.status_code == 302
    created = User.query.filter_by(nameUser='new_user').first()
    assert created is not None
    assert created.check_password('new_password')


def test_register_rejects_short_password(client):
    client.post('/User/add', data={'nameUser': 'corto', 'passwordUser': '123'})
    assert User.query.filter_by(nameUser='corto').first() is None


def test_user_pages_require_login(client, user):
    for url in ['/User/', '/User/js', f'/User/detail/{user.idUser}',
                f'/User/edit/{user.idUser}', f'/User/qr/{user.idUser}']:
        assert client.get(url).status_code == 302, url
    assert client.post(f'/User/delete/{user.idUser}').status_code == 302
    assert db.session.get(User, user.idUser) is not None


def test_async_user_api_is_gone(client):
    assert client.get('/UserAsync/index').status_code == 404


def test_index_does_not_leak_passwords(logged_client, user, other_user):
    response = logged_client.get('/User/')
    assert response.status_code == 200
    assert b"test_user" in response.data
    assert user.passwordUser.encode() not in response.data
    assert b"otro" not in response.data


def test_cannot_edit_other_user(logged_client, other_user):
    response = logged_client.post(f'/User/edit/{other_user.idUser}', data={
        'nameUser': 'hackeado', 'passwordUser': 'hackeado123',
    })
    assert response.status_code == 403
    assert db.session.get(User, other_user.idUser).nameUser == 'otro'


def test_edit_own_user(logged_client, user):
    response = logged_client.post(f'/User/edit/{user.idUser}', data={
        'nameUser': 'updated_user', 'passwordUser': 'updated_password',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"updated_user" in response.data
    assert db.session.get(User, user.idUser).check_password('updated_password')


def test_delete_requires_post(logged_client, user):
    assert logged_client.get(f'/User/delete/{user.idUser}').status_code == 405


def test_delete_own_user_removes_data(logged_client, user):
    from app.models.habitos import Habit
    db.session.add(Habit(idUser=user.idUser, habitName='h', habitFreq='Diaria', habitCategory='salud'))
    db.session.commit()
    response = logged_client.post(f'/User/delete/{user.idUser}')
    assert response.status_code == 302
    assert db.session.get(User, user.idUser) is None
    assert Habit.query.filter_by(idUser=user.idUser).count() == 0
