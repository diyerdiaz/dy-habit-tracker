from app import db
from datetime import date, datetime, timedelta


class Recuperacion(db.Model):
    """Un día perdido de un hábito que se recuperó haciéndolo otro día.

    Solo se puede recuperar dentro de la misma semana (lunes a domingo) y en un
    día de descanso del hábito: si el hábito toca los 7 días no hay día libre
    para recuperarlo.
    """
    __tablename__ = 'recuperaciones'

    idRecuperacion = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idHabit = db.Column(db.Integer, db.ForeignKey('habits.idHabit', ondelete='CASCADE'), nullable=False)
    fechaPerdida = db.Column(db.Date, nullable=False)
    fechaRecuperada = db.Column(db.Date, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        # Un día perdido se recupera una sola vez, y cada día libre recupera un solo día
        db.UniqueConstraint('idHabit', 'fechaPerdida', name='uq_recup_habit_perdida'),
        db.UniqueConstraint('idHabit', 'fechaRecuperada', name='uq_recup_habit_recuperada'),
    )


def inicio_semana(fecha):
    return fecha - timedelta(days=fecha.weekday())


def semana_completa(habit):
    """True si el hábito toca todos los días: no queda día libre para recuperar."""
    return len(habit.dias_lista()) == 7


def dias_perdidos(habit, hechos, hoy=None):
    """Días de esta semana (antes de hoy) en que tocaba el hábito y no se hizo.
    `hechos` es el conjunto de fechas en que el hábito sí se marcó."""
    hoy = hoy or date.today()
    creado = habit.createdAt.date() if habit.createdAt else hoy
    perdidos = []
    cursor = max(inicio_semana(hoy), creado)
    while cursor < hoy:
        if habit.toca_el(cursor) and cursor not in hechos:
            perdidos.append(cursor)
        cursor += timedelta(days=1)
    return perdidos


def puede_recuperar_hoy(habit, recuperado_hoy, hoy=None):
    """Hoy debe ser día de descanso del hábito y no haber recuperado ya otro día con él."""
    hoy = hoy or date.today()
    return (habit.habitState == 'Activo'
            and not semana_completa(habit)
            and hoy.weekday() not in habit.dias_lista()
            and not recuperado_hoy)
