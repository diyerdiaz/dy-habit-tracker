from app import db
from datetime import datetime

class Habit(db.Model):
    __tablename__ = 'habits'
    idHabit = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    habitName = db.Column(db.String(120), nullable=False)
    habitDesc = db.Column(db.String(255), nullable=True)
    habitFreq = db.Column(db.String(50), nullable=False)
    habitCategory = db.Column(db.String(50), nullable=False)
    habitState = db.Column(db.String(50), default='Activo')
    createdAt = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "idHabit": self.idHabit,
            "idUser": self.idUser,
            "habitName": self.habitName,
            "habitDesc": self.habitDesc,
            "habitFreq": self.habitFreq,
            "habitCategory": self.habitCategory,
            "habitState": self.habitState,
            "createdAt": self.createdAt.strftime('%Y-%m-%d %H:%M:%S')
        }
