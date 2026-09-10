from app import db
from datetime import datetime

class Castigo(db.Model):
    __tablename__ = 'castigos'
    idCastigo = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    castigoName = db.Column(db.String(120), nullable=False)
    castigoDesc = db.Column(db.String(255), nullable=True)
    castigoCategory = db.Column(db.String(50), nullable=False)
    castigoState = db.Column(db.String(50), default='Pendiente') # Pendiente, En progreso, Completado
    createdAt = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "idCastigo": self.idCastigo,
            "idUser": self.idUser,
            "castigoName": self.castigoName,
            "castigoDesc": self.castigoDesc,
            "castigoCategory": self.castigoCategory,
            "castigoState": self.castigoState,
            "createdAt": self.createdAt.strftime('%Y-%m-%d %H:%M:%S')
        }
