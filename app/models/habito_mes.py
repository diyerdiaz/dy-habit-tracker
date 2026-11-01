from app import db


class HabitoMes(db.Model):
    """Días y estado que tuvo un hábito hasta el final de un mes.

    Se guarda antes de cambiar el hábito en un mes nuevo, para que el plan de
    ese mes no cambie las estadísticas de los anteriores. Vale para ese mes y
    para los de atrás que no tengan su propia fila.
    """
    __tablename__ = 'habitos_mes'

    idHabitoMes = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idHabit = db.Column(db.Integer, db.ForeignKey('habits.idHabit'), nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    diasSemana = db.Column(db.String(20), nullable=True)  # NULL = todos los días
    habitState = db.Column(db.String(50), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('idHabit', 'anio', 'mes', name='uq_habito_mes'),
    )
