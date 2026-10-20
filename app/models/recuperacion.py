from app import db
from datetime import date, datetime, timedelta

# Veces que se puede recuperar cada hábito en un mes
MAX_POR_MES = 3


class Recuperacion(db.Model):
    """Un día perdido de un hábito que se recuperó haciéndolo en uno de sus días libres.

    Reglas: solo en un día que al hábito no le toca, un solo hábito recuperado
    por día (entre todos) y máximo MAX_POR_MES recuperaciones por hábito al mes.
    """
    __tablename__ = 'recuperaciones_dia'

    idRecuperacion = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idHabit = db.Column(db.Integer, db.ForeignKey('habits.idHabit'), nullable=False)
    fechaPerdida = db.Column(db.Date, nullable=False)
    fechaRecuperada = db.Column(db.Date, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('idHabit', 'fechaPerdida', name='uq_recup_habit_perdida'),
        # Un solo hábito recuperado por día
        db.UniqueConstraint('idUser', 'fechaRecuperada', name='uq_recup_user_dia'),
    )


def inicio_mes(fecha):
    return fecha.replace(day=1)


def dias_perdidos(habit, hechos, hoy=None):
    """Días de este mes (antes de hoy) en que tocaba el hábito y no se hizo.
    `hechos` es el conjunto de fechas en que el hábito sí se marcó."""
    hoy = hoy or date.today()
    creado = habit.createdAt.date() if habit.createdAt else hoy
    perdidos = []
    cursor = max(inicio_mes(hoy), creado)
    while cursor < hoy:
        if habit.toca_el(cursor) and cursor not in hechos:
            perdidos.append(cursor)
        cursor += timedelta(days=1)
    return perdidos


def dia_libre(habit, hoy=None):
    """True si hoy al hábito no le toca (y está activo): es su día libre."""
    hoy = hoy or date.today()
    return habit.habitState == 'Activo' and hoy.weekday() not in habit.dias_lista()
