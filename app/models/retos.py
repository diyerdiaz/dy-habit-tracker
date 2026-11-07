from datetime import datetime

from app import db

# Estados de un reto
PENDIENTE = 'Pendiente'    # el admin lo creó; el usuario aún no responde
EN_CURSO = 'En curso'      # aceptado: cada día del reto hay que marcar "Cumplí hoy"
GANADO = 'Ganado'
PERDIDO = 'Perdido'
RECHAZADO = 'Rechazado'
VENCIDO = 'Vencido'        # empezó sin que el usuario respondiera
CANCELADO = 'Cancelado'    # lo canceló el admin
ABIERTOS = (PENDIENTE, EN_CURSO)
CERRADOS_CON_RESULTADO = (GANADO, PERDIDO)


class Reto(db.Model):
    """Reto libre que el admin le pone a un usuario (por ejemplo, "no ver redes
    sociales durante 5 días") con XP apostado: si cumple todos los días gana la
    apuesta; si deja un día sin cumplir, la pierde."""
    # No se llama 'retos': un intento anterior (que no llegó al código) dejó esa
    # tabla con otras columnas en algunas bases locales
    __tablename__ = 'retos_usuario'

    idReto = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(500), nullable=True)
    fechaInicio = db.Column(db.Date, nullable=False)
    fechaFin = db.Column(db.Date, nullable=False)
    apuesta = db.Column(db.Integer, nullable=False, default=0)
    # Todo o nada: la apuesta es todo el XP que tenga al aceptar (se fija en `apuesta`)
    todoXp = db.Column(db.Boolean, nullable=False, default=False)
    estado = db.Column(db.String(20), nullable=False, default=PENDIENTE)
    # El usuario ya vio que ganó o perdió: el botón "Retos" deja de aparecer por esto
    resultadoVisto = db.Column(db.Boolean, nullable=False, default=False)
    createdAt = db.Column(db.DateTime, default=datetime.now)
    cerradoEn = db.Column(db.DateTime, nullable=True)

    dias = db.relationship('RetoDia', backref='reto', cascade='all, delete-orphan', lazy='dynamic')

    def total_dias(self):
        return (self.fechaFin - self.fechaInicio).days + 1


class RetoDia(db.Model):
    """Un día en que el usuario marcó "Cumplí hoy" en su reto."""
    __tablename__ = 'retos_usuario_dias'

    idRetoDia = db.Column(db.Integer, primary_key=True)
    idReto = db.Column(db.Integer, db.ForeignKey('retos_usuario.idReto'), nullable=False)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('idReto', 'fecha', name='uq_reto_usuario_dia'),
    )
