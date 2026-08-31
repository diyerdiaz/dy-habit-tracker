from app import create_app, db
from app.models.users import User

app = create_app()

with app.app_context():
    # Check if user already exists
    user = User.query.filter_by(nameUser='diyer').first()
    if not user:
        new_user = User(nameUser='diyer', passwordUser='123456')
        db.session.add(new_user)
        db.session.commit()
        print("User 'diyer' created successfully with password '123456'.")
    else:
        print("User 'diyer' already exists.")
