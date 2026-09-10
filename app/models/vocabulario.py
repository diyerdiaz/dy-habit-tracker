from app import db
from datetime import datetime

class Vocabulario(db.Model):
    __tablename__ = 'vocabularios'
    idVocab = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    significado = db.Column(db.String(255), nullable=False)
    ejemplos = db.Column(db.String(500), nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "idVocab": self.idVocab,
            "idUser": self.idUser,
            "nombre": self.nombre,
            "significado": self.significado,
            "ejemplos": self.ejemplos,
            "createdAt": self.createdAt.strftime('%Y-%m-%d %H:%M:%S')
        }
