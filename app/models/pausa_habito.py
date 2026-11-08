from datetime import datetime

from app import db


class PausaHabito(db.Model):
    """Días en que un hábito estuvo pausado a mitad de mes (desde "Gestión de
    hábitos" o el panel del admin). Esos días no cuentan como pendientes ni
    perdidos; los de antes y después de la pausa sí. `hasta` NULL = sigue pausado.
    """
    __tablename__ = 'pausas_habito'

    idPausa = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idHabit = db.Column(db.Integer, db.ForeignKey('habits.idHabit'), nullable=False)
    desde = db.Column(db.Date, nullable=False)
    hasta = db.Column(db.Date, nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.now)
