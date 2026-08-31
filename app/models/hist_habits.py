from app import db
from datetime import datetime

class HistHabit(db.Model):
    __tablename__ = 'hist_habits'
    idHist = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idHabit = db.Column(db.Integer, db.ForeignKey('habits.idHabit'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('idHabit', 'fecha', name='uq_hist_habit_fecha'),
    )
