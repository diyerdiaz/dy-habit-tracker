from app import db
from datetime import datetime

class ShadowingSesion(db.Model):
    __tablename__ = 'shadowing_sesiones'
    idSesion = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    duracionSegundos = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "idSesion": self.idSesion,
            "duracionSegundos": self.duracionSegundos,
            "fecha": self.fecha.strftime('%Y-%m-%d %H:%M:%S')
        }
