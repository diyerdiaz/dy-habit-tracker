"""Convierte a hash todas las contraseñas que sigan guardadas en texto plano.

Uso:  python migrar_passwords.py
Antes de modificar nada crea una copia de seguridad de la base de datos.
(Si no lo ejecutas, cada contraseña antigua se convierte sola la próxima vez
que ese usuario inicie sesión.)
"""
import os
import shutil
from datetime import datetime
from app import create_app, db
from app.models.users import User

app = create_app()

with app.app_context():
    db_path = db.engine.url.database
    if db_path and os.path.exists(db_path):
        backup = f"{db_path}.bak-{datetime.now():%Y%m%d-%H%M%S}"
        shutil.copy2(db_path, backup)
        print(f"Copia de seguridad: {backup}")

    migrados = 0
    for user in User.query.all():
        if not user.password_is_hashed():
            user.set_password(user.passwordUser)
            migrados += 1
    db.session.commit()
    print(f"Contraseñas convertidas a hash: {migrados}")
