from app import create_app, db
import pytest

@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        db.create_all()  # Create tables within the context
        yield app
        db.session.remove()  # Cleanup session objects
        db.drop_all()
  

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def user(app):
    from app.models.users import User
    user = User(nameUser="test_user", passwordUser="test_password")
    db.session.add(user)
    db.session.commit()  # Commit changes within the context
    yield user    
  # Cleanup changes within the context