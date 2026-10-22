from app import db
from datetime import date, datetime, timedelta

# Veces que hay que hacer el hábito en sus días libres para completar un día perdido
VECES_PARA_RECUPERAR = 3


class SesionRecuperacion(db.Model):
    """Una vez que se hizo un hábito en un día que no le tocaba (su día libre).

    Solo se registra un hábito por día (entre todos). Al juntar
    VECES_PARA_RECUPERAR de un mismo hábito en el mes, se gastan para completar
    un día perdido (idRecuperacion queda apuntando a esa recuperación).
    """
    __tablename__ = 'sesiones_recuperacion'

    idSesion = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idHabit = db.Column(db.Integer, db.ForeignKey('habits.idHabit'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    idRecuperacion = db.Column(db.Integer, db.ForeignKey('recuperaciones_dia.idRecuperacion'), nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('idHabit', 'fecha', name='uq_sesion_habit_fecha'),
    )


class Recuperacion(db.Model):
    """Un día perdido de un hábito que se completó con VECES_PARA_RECUPERAR sesiones."""
    __tablename__ = 'recuperaciones_dia'

    idRecuperacion = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    idHabit = db.Column(db.Integer, db.ForeignKey('habits.idHabit'), nullable=False)
    fechaPerdida = db.Column(db.Date, nullable=False)
    fechaRecuperada = db.Column(db.Date, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('idHabit', 'fechaPerdida', name='uq_recup_habit_perdida'),
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


def dias_libres_que_quedan(habit, desde, hoy=None):
    """Días libres del hábito desde `desde` hasta fin de mes: las veces que aún se pueden sumar."""
    hoy = hoy or date.today()
    fin = (inicio_mes(hoy) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    dias = set(habit.dias_lista())
    cuenta = 0
    cursor = desde
    while cursor <= fin:
        if cursor.weekday() not in dias:
            cuenta += 1
        cursor += timedelta(days=1)
    return cuenta


def cuantos_se_pueden_recuperar(perdidos, veces, libres_que_quedan):
    """Días perdidos que todavía se alcanzan a completar este mes.

    Cada día completado gasta VECES_PARA_RECUPERAR veces; las veces solo valen
    dentro del mes, así que lo que no alcance a juntarse antes de fin de mes no
    se puede recuperar.
    """
    return min(len(perdidos), (veces + libres_que_quedan) // VECES_PARA_RECUPERAR)
