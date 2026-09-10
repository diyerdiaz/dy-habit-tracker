from app import db
from datetime import datetime

class VocabularioRegistro(db.Model):
    __tablename__ = 'vocabulario_registros'
    idRegistro = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idVocab = db.Column(db.Integer, db.ForeignKey('vocabularios.idVocab'), nullable=True)
    palabraNombre = db.Column(db.String(120), nullable=False)
    calificacion = db.Column(db.String(20), nullable=False)  # facil, medio, dificil
    fecha = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "idRegistro": self.idRegistro,
            "idVocab": self.idVocab,
            "palabraNombre": self.palabraNombre,
            "calificacion": self.calificacion,
            "fecha": self.fecha.strftime('%Y-%m-%d %H:%M:%S')
        }
