from app import db

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), primary_key=True)
    xpTotal = db.Column(db.Integer, nullable=False, default=0)
    rachaActual = db.Column(db.Integer, nullable=False, default=0)
    rachaMaxima = db.Column(db.Integer, nullable=False, default=0)
    habitosCompletados = db.Column(db.Integer, nullable=False, default=0)
    ultimaFechaActividad = db.Column(db.Date, nullable=True)
    ultimaFechaPenalizada = db.Column(db.Date, nullable=True)
