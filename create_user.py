"""Crea un usuario inicial.

Uso:  python create_user.py <usuario>
La contraseña se pide por teclado (no queda en el historial de la terminal).
"""
import sys
import getpass
from app import create_app, db
from app.services.esquema import actualizar_esquema
from app.models.users import User

app = create_app()

with app.app_context():
    actualizar_esquema()
    name = sys.argv[1] if len(sys.argv) > 1 else input("Usuario: ").strip()
    if not name:
        sys.exit("Debes indicar un nombre de usuario.")
    if User.query.filter_by(nameUser=name).first():
        sys.exit(f"El usuario '{name}' ya existe.")
    password = getpass.getpass("Contraseña: ")
    if len(password) < 6:
        sys.exit("La contraseña debe tener al menos 6 caracteres.")
    if password != getpass.getpass("Repite la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    db.session.add(User(nameUser=name, password=password))
    db.session.commit()
    print(f"Usuario '{name}' creado correctamente.")
