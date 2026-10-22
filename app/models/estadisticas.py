"""Estadísticas de cumplimiento de cada hábito por mes.

El porcentaje de un hábito en un mes es: días que se marcó como hecho /
días que le tocaba (según sus días de la semana), contando solo desde que
se creó y hasta hoy. Los días de descanso no cuentan en contra.
"""

from calendar import Calendar, monthrange
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


# ── Comparar meses ──

MAX_MESES_COMPARAR = 12


def leer_meses(textos, hoy=None, por_defecto=3):
    """Convierte una lista de 'AAAA-MM' en [(anio, mes), ...] del más antiguo al más reciente.

    Ignora los inválidos o futuros y los repetidos. Si no queda ninguno, devuelve
    los últimos `por_defecto` meses hasta el actual.
    """
    hoy = hoy or date.today()
    elegidos = set()
    for texto in textos or []:
        try:
            anio, mes = (int(p) for p in texto.split('-'))
        except ValueError:
            continue
        if 1 <= mes <= 12 and anio >= 2000 and (anio, mes) <= (hoy.year, hoy.month):
            elegidos.add((anio, mes))
    if not elegidos:
        anio, mes = hoy.year, hoy.month
        for _ in range(por_defecto):
            elegidos.add((anio, mes))
            anio, mes = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
    return sorted(elegidos)[-MAX_MESES_COMPARAR:]


def comparar_meses(idUser, meses, hoy=None):
    """Porcentaje de cada hábito en cada uno de los meses dados (lista de (anio, mes)).

    Devuelve una fila por hábito con un valor por mes (None si el hábito no
    existía ese mes) y la diferencia en puntos entre el primer y el último mes
    en que tuvo datos.
    """
    hoy = hoy or date.today()
    columnas = []
    filas = {}
    for i, (anio, mes) in enumerate(meses):
        stats = estadisticas_del_mes(idUser, anio, mes, hoy)
        columnas.append({
            'valor': f"{anio}-{mes:02d}",
            'nombre': nombre_mes(anio, mes),
            'promedio': stats['promedio'],
            'nivel': stats['nivel_promedio'],
        })
        for h in stats['habitos']:
            fila = filas.setdefault(h['id'], {
                'id': h['id'],
                'nombre': h['nombre'],
                'categoria': h['categoria'],
                'valores': [None] * len(meses),
            })
            fila['valores'][i] = {
                'pct': h['pct'],
                'nivel': h['nivel'],
                'cumplidos': h['cumplidos'],
                'programados': h['programados'],
            }

    def _diferencia(valores):
        pcts = [v['pct'] for v in valores if v and v['pct'] is not None]
        return pcts[-1] - pcts[0] if len(pcts) > 1 else None

    habitos = sorted(filas.values(), key=lambda f: f['nombre'].lower())
    for fila in habitos:
        fila['diferencia'] = _diferencia(fila['valores'])

    promedios = [c['promedio'] for c in columnas if c['promedio'] is not None]
    return {
        'meses': columnas,
        'habitos': habitos,
        'diferencia_promedio': promedios[-1] - promedios[0] if len(promedios) > 1 else None,
    }


# ── Calendario ──

DIAS_CORTOS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def calendario_del_mes(idUser, anio, mes, hoy=None):
    """Semanas del mes (de lunes a domingo) con los hábitos hechos cada día.

    Cada día trae `hechos` (los que marcaste) y `pendientes` (los que te tocaban
    y no hiciste). Los días de otros meses que completan la semana van con
    `fuera=True` y sin datos.
    """
    hoy = hoy or date.today()
    inicio_mes = date(anio, mes, 1)
    fin_mes = date(anio, mes, monthrange(anio, mes)[1])

    habitos = Habit.query.filter_by(idUser=idUser).order_by(Habit.habitName).all()
    por_id = {h.idHabit: h for h in habitos}

    hechos_por_dia = {}
    for registro in HistHabit.query.filter(
        HistHabit.idUser == idUser,
        HistHabit.fecha >= inicio_mes,
        HistHabit.fecha <= fin_mes,
    ).all():
        if registro.idHabit in por_id:
            hechos_por_dia.setdefault(registro.fecha, set()).add(registro.idHabit)

    semanas = []
    total_hechos = 0
    dias_con_algo = 0
    for semana in Calendar(firstweekday=0).monthdatescalendar(anio, mes):
        fila = []
        for dia in semana:
            if dia.month != mes:
                fila.append({'fecha': dia, 'numero': dia.day, 'fuera': True})
                continue
            hechos_ids = hechos_por_dia.get(dia, set())
            tocaban = [h for h in habitos
                       if h.createdAt.date() <= dia and dia.weekday() in h.dias_lista()]
            hechos = [por_id[i].habitName for i in sorted(hechos_ids, key=lambda i: por_id[i].habitName.lower())]
            futuro = dia > hoy
            pendientes = [] if futuro else [h.habitName for h in tocaban if h.idHabit not in hechos_ids]
            cumplidos = sum(1 for h in tocaban if h.idHabit in hechos_ids)
            pct = round(cumplidos / len(tocaban) * 100) if tocaban and not futuro else None
            total_hechos += len(hechos)
            dias_con_algo += 1 if hechos else 0
            fila.append({
                'fecha': dia,
                'numero': dia.day,
                'fuera': False,
                'futuro': futuro,
                'es_hoy': dia == hoy,
                'hechos': hechos,
                'pendientes': pendientes,
                'tocaban': len(tocaban),
                'pct': pct,
                'nivel': _nivel(pct),
            })
        semanas.append(fila)

    return {
        'semanas': semanas,
        'dias_semana': DIAS_CORTOS,
        'total_hechos': total_hechos,
        'dias_con_algo': dias_con_algo,
    }
