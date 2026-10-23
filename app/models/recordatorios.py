from app import db
from datetime import datetime

# Máximo de recordatorios por usuario (evita llenar la bandeja de correos)
MAX_RECORDATORIOS = 5


class Recordatorio(db.Model):
    """Hora del día en que se envía al usuario un correo con sus hábitos pendientes."""
    __tablename__ = 'recordatorios'
    idRecordatorio = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    # Hora local en formato "HH:MM" (24 h)
    hora = db.Column(db.String(5), nullable=False)
    # Último día en que ya se revisó/envió: evita mandar dos correos el mismo día
    ultimoEnvio = db.Column(db.Date, nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('idUser', 'hora', name='uq_recordatorio_user_hora'),
    )

    def hora_time(self):
        return datetime.strptime(self.hora, '%H:%M').time()

    def hora_texto(self):
        """Hora en formato 12 h, p. ej. "8:00 p. m."."""
        t = self.hora_time()
        sufijo = 'a. m.' if t.hour < 12 else 'p. m.'
        return f"{(t.hour % 12) or 12}:{t.minute:02d} {sufijo}"
