"""Días que le tocaban a cada hábito en un mes: el plan de un mes nuevo no
cambia lo que ya pasó en los anteriores."""

from datetime import date, timedelta
from sqlalchemy import and_, or_
from app import db
from app.models.habito_mes import HabitoMes
from app.models.habitos import leer_dias
from app.models.pausa_habito import PausaHabito


def pausa_abierta(habit):
    """La pausa a mitad de mes que sigue en curso, o None."""
    return PausaHabito.query.filter_by(idHabit=habit.idHabit, hasta=None).first()


def guardar_mes_anterior(habit, hoy=None, estado=None):
    """Llamar ANTES de cambiar el hábito. No hace commit: lo hace quien llama."""
    primer_dia = (hoy or date.today()).replace(day=1)
    if habit.createdAt.date() >= primer_dia:
        return  # el mes pasado todavía no existía
    if estado is None and habit.habitState == 'Pausado' and pausa_abierta(habit):
        # Con su pausa guardada, el mes contaba hasta el día en que se pausó
        estado = 'Activo'
    ultimo = primer_dia - timedelta(days=1)
    if not HabitoMes.query.filter_by(idHabit=habit.idHabit, anio=ultimo.year, mes=ultimo.month).first():
        db.session.add(HabitoMes(idUser=habit.idUser, idHabit=habit.idHabit, anio=ultimo.year, mes=ultimo.month,
                                 diasSemana=habit.diasSemana, habitState=estado or habit.habitState))


def pausar_o_reanudar(habit, hoy=None):
    """Pausa el hábito desde hoy o lo reanuda desde hoy, guardando las fechas de la
    pausa: solo esos días dejan de contar en las estadísticas, el resto del mes
    sigue igual. Devuelve el estado nuevo. No hace commit: lo hace quien llama."""
    hoy = hoy or date.today()
    guardar_mes_anterior(habit, hoy)
    if habit.habitState == 'Pausado':
        pausa = pausa_abierta(habit)
        if pausa and pausa.desde >= hoy:
            db.session.delete(pausa)  # se pausó y reanudó el mismo día
        elif pausa:
            pausa.hasta = hoy - timedelta(days=1)
        habit.habitState = 'Activo'
    else:
        db.session.add(PausaHabito(idUser=habit.idUser, idHabit=habit.idHabit, desde=hoy))
        habit.habitState = 'Pausado'
    return habit.habitState


def cerrar_pausas(habits, hoy=None):
    """Al confirmar el plan de un mes nuevo, las pausas abiertas terminan el último
    día del mes anterior: desde ahora manda el plan. No hace commit."""
    primer_dia = (hoy or date.today()).replace(day=1)
    for habit in habits:
        pausa = pausa_abierta(habit)
        if pausa and pausa.desde >= primer_dia:
            db.session.delete(pausa)
        elif pausa:
            pausa.hasta = primer_dia - timedelta(days=1)


def pausas_del_usuario(idUser):
    """{idHabit: [(desde, hasta), ...]} con las pausas a mitad de mes del usuario."""
    pausas = {}
    for p in PausaHabito.query.filter_by(idUser=idUser).all():
        pausas.setdefault(p.idHabit, []).append((p.desde, p.hasta or date.max))
    return pausas


def pausas_abiertas(idUser):
    """ids de los hábitos que siguen pausados con sus fechas guardadas."""
    return {p.idHabit for p in PausaHabito.query.filter_by(idUser=idUser, hasta=None)}


def en_pausa(pausas, idHabit, dia):
    return any(desde <= dia <= hasta for desde, hasta in pausas.get(idHabit, ()))


def dias_del_mes(idUser, habits, anio, mes):
    """{idHabit: días de la semana que le tocaban ese mes}. Pausado = ninguno,
    salvo que la pausa tenga sus fechas guardadas: entonces solo esos días se
    quitan (con `en_pausa`)."""
    abiertas = pausas_abiertas(idUser)
    filas = HabitoMes.query.filter(
        HabitoMes.idUser == idUser,
        or_(HabitoMes.anio > anio, and_(HabitoMes.anio == anio, HabitoMes.mes >= mes)),
    ).order_by(HabitoMes.anio.desc(), HabitoMes.mes.desc()).all()
    # Del más reciente al más antiguo: se queda la fila más cercana a ese mes
    guardados = {fila.idHabit: fila for fila in filas}

    dias = {}
    for habit in habits:
        fila = guardados.get(habit.idHabit, habit)
        activo = fila.habitState == 'Activo' or (
            fila is habit and habit.habitState == 'Pausado' and habit.idHabit in abiertas)
        dias[habit.idHabit] = set(leer_dias(fila.diasSemana)) if activo else set()
    return dias
