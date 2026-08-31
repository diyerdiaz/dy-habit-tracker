from app import db
from datetime import datetime, date

class Tarea(db.Model):
    __tablename__ = 'tareas'
    idTarea = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    completada = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
