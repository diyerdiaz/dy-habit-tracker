from datetime import datetime

from app import db


class MedallaVista(db.Model):
    """Medallas ganadas que el usuario ya vio anunciadas. Las medallas se calculan
    al vuelo; esta tabla solo sirve para saber cuáles son nuevas y avisarlas."""
    __tablename__ = 'medallas_vistas'

    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), primary_key=True)
    idMedalla = db.Column(db.String(60), primary_key=True)
    vistaEn = db.Column(db.DateTime, default=datetime.now)
