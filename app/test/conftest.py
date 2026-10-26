import pytest
from app import create_app, db

TEST_PASSWORD = "Test_password1"


@pytest.fixture
def app(tmp_path_factory):
    # Base de datos EN MEMORIA: los tests nunca tocan instance/flaskdb.sqlite
    app = create_app({
        # Archivos subidos en una carpeta temporal: los tests nunca tocan instance/uploads
        "UPLOAD_FOLDER": str(tmp_path_factory.mktemp("uploads")),
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
        # Los tests nunca usan el correo real aunque exista un .env con datos
        "MAIL_ENABLED": False,
        "MAIL_USERNAME": "",
        "MAIL_PASSWORD": "",
    })
    with app.app_context():
        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
        assert "instance" not in app.config["UPLOAD_FOLDER"]
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    from app.models.users import User
    user = User(nameUser="test_user", password=TEST_PASSWORD)
    db.session.add(user)
    db.session.commit()
    yield user


@pytest.fixture
def other_user(app):
    from app.models.users import User
    other = User(nameUser="otro", password="Otra_clave1")
    db.session.add(other)
    db.session.commit()
    yield other


@pytest.fixture
def logged_client(client, user):
    client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD})
    return client
