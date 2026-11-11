from datetime import datetime

from app import db


class MedallaAnunciada(db.Model):
    """Medallas ganadas cuyo aviso obligatorio ("¡Ganaste una medalla!") el
    usuario ya aceptó. Las medallas se calculan al vuelo; esta tabla solo sirve
    para que cada aviso salga una única vez, aunque la app se actualice."""
    __tablename__ = 'medallas_anunciadas'

    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), primary_key=True)
    idMedalla = db.Column(db.String(60), primary_key=True)
    vistaEn = db.Column(db.DateTime, default=datetime.now)
