"""Días que le tocaban a cada hábito en un mes: el plan de un mes nuevo no
cambia lo que ya pasó en los anteriores."""

from datetime import date, timedelta
from sqlalchemy import and_, or_
from app import db
from app.models.habito_mes import HabitoMes
from app.models.habitos import leer_dias


def guardar_mes_anterior(habit, hoy=None, estado=None):
    """Llamar ANTES de cambiar el hábito. No hace commit: lo hace quien llama."""
    primer_dia = (hoy or date.today()).replace(day=1)
    if habit.createdAt.date() >= primer_dia:
        return  # el mes pasado todavía no existía
    ultimo = primer_dia - timedelta(days=1)
    if not HabitoMes.query.filter_by(idHabit=habit.idHabit, anio=ultimo.year, mes=ultimo.month).first():
        db.session.add(HabitoMes(idUser=habit.idUser, idHabit=habit.idHabit, anio=ultimo.year, mes=ultimo.month,
                                 diasSemana=habit.diasSemana, habitState=estado or habit.habitState))


def dias_del_mes(idUser, habits, anio, mes):
    """{idHabit: días de la semana que le tocaban ese mes}. Pausado = ninguno."""
    filas = HabitoMes.query.filter(
        HabitoMes.idUser == idUser,
        or_(HabitoMes.anio > anio, and_(HabitoMes.anio == anio, HabitoMes.mes >= mes)),
    ).order_by(HabitoMes.anio.desc(), HabitoMes.mes.desc()).all()
    # Del más reciente al más antiguo: se queda la fila más cercana a ese mes
    guardados = {fila.idHabit: fila for fila in filas}

    dias = {}
    for habit in habits:
        fila = guardados.get(habit.idHabit, habit)
        dias[habit.idHabit] = set(leer_dias(fila.diasSemana)) if fila.habitState == 'Activo' else set()
    return dias
