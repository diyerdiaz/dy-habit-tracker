from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import qrcode
import json
from io import BytesIO
import base64

# Prefijos de los hashes que genera werkzeug (scrypt por defecto, pbkdf2 en versiones viejas)
_HASH_PREFIXES = ('scrypt:', 'pbkdf2:')


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    idUser = db.Column(db.Integer, primary_key=True)
    nameUser = db.Column(db.String(80), unique=True, nullable=False)
    # Guarda el HASH de la contraseña, nunca el texto plano
    passwordUser = db.Column(db.String(255), nullable=False)

    def __init__(self, nameUser, password=None, **kwargs):
        # Compatibilidad: User(nameUser=..., passwordUser=...) también hashea
        password = password if password is not None else kwargs.pop('passwordUser', None)
        super().__init__(nameUser=nameUser, **kwargs)
        if password is not None:
            self.set_password(password)

    def get_id(self):
        return str(self.idUser)

    def set_password(self, password):
        self.passwordUser = generate_password_hash(password)

    def password_is_hashed(self):
        return bool(self.passwordUser) and self.passwordUser.startswith(_HASH_PREFIXES)

    def check_password(self, password):
        """Valida la contraseña. Si el usuario aún tiene una contraseña antigua en
        texto plano, la valida y la convierte a hash en ese mismo momento."""
        if not self.passwordUser or password is None:
            return False
        if self.password_is_hashed():
            return check_password_hash(self.passwordUser, password)
        # Contraseña heredada en texto plano
        if secrets_compare(self.passwordUser, password):
            self.set_password(password)
            db.session.commit()
            return True
        return False

    def to_dict(self):
        # Nunca exponer la contraseña (ni su hash)
        return {
            "idUser": self.idUser,
            "nameUser": self.nameUser,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def generate_qr(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps({"ID": self.idUser, "Name": self.nameUser}))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')


def secrets_compare(a, b):
    import hmac
    return hmac.compare_digest(str(a).encode('utf-8'), str(b).encode('utf-8'))
