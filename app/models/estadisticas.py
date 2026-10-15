"""Estadísticas de cumplimiento de cada hábito por mes.

El porcentaje de un hábito en un mes es: días que se marcó como hecho /
días que le tocaba (según sus días de la semana), contando solo desde que
se creó y hasta hoy. Los días de descanso no cuentan en contra.
"""

from calendar import monthrange
from datetime import date, timedelta
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


def nombre_mes(anio, mes):
    return f"{MESES[mes - 1]} {anio}"


def leer_mes(texto, hoy=None):
    """Convierte 'AAAA-MM' en (anio, mes). Si no es válido o es futuro, devuelve el mes actual."""
    hoy = hoy or date.today()
    try:
        anio, mes = (int(p) for p in (texto or '').split('-'))
        if 1 <= mes <= 12 and (anio, mes) <= (hoy.year, hoy.month) and anio >= 2000:
            return anio, mes
    except ValueError:
        pass
    return hoy.year, hoy.month


def meses_disponibles(idUser, hoy=None):
    """Meses desde el primer hábito creado hasta el actual, del más reciente al más antiguo."""
    hoy = hoy or date.today()
    primero = Habit.query.filter_by(idUser=idUser).order_by(Habit.createdAt).first()
    inicio = primero.createdAt.date() if primero else hoy
    meses = []
    anio, mes = hoy.year, hoy.month
    while (anio, mes) >= (inicio.year, inicio.month):
        meses.append({'valor': f"{anio}-{mes:02d}", 'nombre': nombre_mes(anio, mes)})
        anio, mes = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
    return meses


def _nivel(pct):
    if pct is None:
        return 'sin-datos'
    if pct >= 80:
        return 'alto'
    if pct >= 50:
        return 'medio'
    return 'bajo'


def estadisticas_del_mes(idUser, anio, mes, hoy=None):
    hoy = hoy or date.today()
    inicio_mes = date(anio, mes, 1)
    fin_mes = min(date(anio, mes, monthrange(anio, mes)[1]), hoy)

    hechos_por_habito = {}
    for registro in HistHabit.query.filter(
        HistHabit.idUser == idUser,
        HistHabit.fecha >= inicio_mes,
        HistHabit.fecha <= fin_mes,
    ).all():
        hechos_por_habito.setdefault(registro.idHabit, set()).add(registro.fecha)

    habitos = []
    for habit in Habit.query.filter_by(idUser=idUser).order_by(Habit.habitName).all():
        desde = max(inicio_mes, habit.createdAt.date())
        dias_semana = set(habit.dias_lista())
        programados = []
        dia = desde
        while dia <= fin_mes:
            if dia.weekday() in dias_semana:
                programados.append(dia)
            dia += timedelta(days=1)

        hechos = hechos_por_habito.get(habit.idHabit, set())
        if not programados and not hechos:
            continue  # el hábito aún no existía ese mes
        cumplidos = sum(1 for d in programados if d in hechos)
        pct = round(cumplidos / len(programados) * 100) if programados else None
        habitos.append({
            'id': habit.idHabit,
            'nombre': habit.habitName,
            'categoria': habit.habitCategory,
            'estado': habit.habitState,
            'programados': len(programados),
            'cumplidos': cumplidos,
            'extra': len(hechos) - cumplidos,  # marcados en días de descanso
            'pct': pct,
            'nivel': _nivel(pct),
        })

    con_datos = [h for h in habitos if h['pct'] is not None]
    promedio = round(sum(h['pct'] for h in con_datos) / len(con_datos)) if con_datos else None
    dias_activos = len({d for fechas in hechos_por_habito.values() for d in fechas})
    return {
        'habitos': habitos,
        'promedio': promedio,
        'nivel_promedio': _nivel(promedio),
        'mejor': max(con_datos, key=lambda h: h['pct']) if con_datos else None,
        'a_mejorar': min(con_datos, key=lambda h: h['pct']) if len(con_datos) > 1 else None,
        'dias_activos': dias_activos,
        'dias_del_mes': (fin_mes - inicio_mes).days + 1 if fin_mes >= inicio_mes else 0,
        'total_cumplidos': sum(h['cumplidos'] for h in habitos),
    }
