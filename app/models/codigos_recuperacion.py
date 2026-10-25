import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from app import db

DIGITOS = 6
MINUTOS_VALIDEZ = 5     # el código deja de servir a los 5 minutos
MAX_INTENTOS = 3        # al tercer código incorrecto se anula
# Tras verificar el código, tiempo para escribir la contraseña nueva
MINUTOS_PARA_CAMBIAR = 10


class CodigoRecuperacion(db.Model):
    """Código de 6 dígitos enviado por correo para recuperar la contraseña.
    Se guarda solo su hash, igual que las contraseñas."""
    __tablename__ = 'codigos_recuperacion'
    idCodigo = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    codigoHash = db.Column(db.String(255), nullable=False)
    expira = db.Column(db.DateTime, nullable=False)
    intentos = db.Column(db.Integer, nullable=False, default=0)
    # Momento en que se escribió bien; desde ahí corre MINUTOS_PARA_CAMBIAR
    verificadoAt = db.Column(db.DateTime, nullable=True)
    # Anulado (se pidió otro, se agotaron los intentos) o ya usado para cambiar la contraseña
    anulado = db.Column(db.Boolean, nullable=False, default=False)
    createdAt = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)

    @classmethod
    def crear(cls, idUser, ahora=None):
        """Anula los códigos anteriores del usuario y crea uno nuevo.
        Devuelve (registro, código en texto) — el texto solo se usa para el correo."""
        ahora = ahora or datetime.now()
        cls.query.filter_by(idUser=idUser, anulado=False).update({'anulado': True})
        codigo = f'{secrets.randbelow(10 ** DIGITOS):0{DIGITOS}d}'
        registro = cls(idUser=idUser, codigoHash=generate_password_hash(codigo),
                       expira=ahora + timedelta(minutes=MINUTOS_VALIDEZ), createdAt=ahora)
        db.session.add(registro)
        db.session.commit()
        return registro, codigo

    @classmethod
    def activo(cls, idUser):
        return (cls.query.filter_by(idUser=idUser, anulado=False)
                .order_by(cls.createdAt.desc()).first())

    def vencido(self, ahora=None):
        return (ahora or datetime.now()) >= self.expira

    def intentos_restantes(self):
        return max(0, MAX_INTENTOS - self.intentos)

    def comprobar(self, codigo, ahora=None):
        """'ok', 'vencido', 'agotado' o 'incorrecto'. Cuenta el intento si es incorrecto."""
        if self.anulado or self.intentos >= MAX_INTENTOS:
            return 'agotado'
        if self.vencido(ahora):
            return 'vencido'
        codigo = (codigo or '').strip()
        if len(codigo) == DIGITOS and codigo.isdigit() and check_password_hash(self.codigoHash, codigo):
            self.verificadoAt = ahora or datetime.now()
            db.session.commit()
            return 'ok'
        self.intentos += 1
        if self.intentos >= MAX_INTENTOS:
            self.anulado = True
        db.session.commit()
        return 'agotado' if self.anulado else 'incorrecto'

    def puede_cambiar(self, ahora=None):
        """True si el código se verificó hace poco y aún no se usó."""
        if self.anulado or not self.verificadoAt:
            return False
        return (ahora or datetime.now()) < self.verificadoAt + timedelta(minutes=MINUTOS_PARA_CAMBIAR)
