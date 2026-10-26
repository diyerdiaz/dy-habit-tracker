from app import db
from datetime import datetime, date

class Tarea(db.Model):
    __tablename__ = 'tareas'
    idTarea = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    completada = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    # Hora local "HH:MM" (24 h) en que se envía un correo si la tarea sigue pendiente
    horaRecordatorio = db.Column(db.String(5), nullable=True)
    # Ya se envió el correo de esta tarea (se reinicia al cambiar la hora o la fecha)
    recordatorioEnviado = db.Column(db.Boolean, nullable=False, default=False)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    def hora_time(self):
        return datetime.strptime(self.horaRecordatorio, '%H:%M').time() if self.horaRecordatorio else None

    def hora_texto(self):
        """Hora del recordatorio en formato 12 h, p. ej. "8:00 p. m."."""
        t = self.hora_time()
        if t is None:
            return ''
        sufijo = 'a. m.' if t.hour < 12 else 'p. m.'
        return f"{(t.hour % 12) or 12}:{t.minute:02d} {sufijo}"
