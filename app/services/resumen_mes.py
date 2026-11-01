"""Resumen del mes que terminó: sale una sola vez, al empezar el mes siguiente,
antes del aviso del plan. Usa los mismos cálculos de la pantalla de Estadísticas."""

from datetime import date, timedelta
from app import db
from app.models.resumen_mensual import ResumenVisto
from app.services.estadisticas import MESES, calendario_del_mes, estadisticas_del_mes


def mes_anterior(fecha):
    ultimo_dia = fecha.replace(day=1) - timedelta(days=1)
    return ultimo_dia.year, ultimo_dia.month


def _mejor_racha(dias):
    """Días seguidos con algo hecho; los días sin hábitos programados no la cortan."""
    mejor = actual = 0
    for dia in dias:
        if dia['hechos']:
            actual += 1
            mejor = max(mejor, actual)
        elif dia['tocaban']:
            actual = 0
    return mejor


def resumen_del_mes(idUser, anio, mes, hoy=None):
    """Estadísticas de un mes para la tarjeta, o None si ese mes no tuvo nada programado."""
    hoy = hoy or date.today()
    stats = estadisticas_del_mes(idUser, anio, mes, hoy)
    con_datos = [h for h in stats['habitos'] if h['pct'] is not None]
    if not con_datos:
        return None

    habitos = sorted(con_datos, key=lambda h: (-h['pct'], -h['cumplidos'], h['nombre'].lower()))
    mejor = habitos[0]
    # Si todos quedaron igual (o solo hay uno), ninguno fue el peor
    peor = habitos[-1] if habitos[-1]['pct'] < mejor['pct'] else None

    calendario = calendario_del_mes(idUser, anio, mes, hoy)
    dias = [d for semana in calendario['semanas'] for d in semana if not d['fuera']]
    con_pct = [d for d in dias if d['pct'] is not None]
    mejor_dia = max(con_pct, key=lambda d: (d['pct'], len(d['hechos'])), default=None)

    nombre = MESES[mes - 1].lower()
    anterior_anio, anterior_mes = mes_anterior(date(anio, mes, 1))
    promedio_anterior = estadisticas_del_mes(idUser, anterior_anio, anterior_mes, hoy)['promedio']
    return {
        'mes': nombre,
        'valor': f"{anio}-{mes:02d}",
        'habitos': habitos,
        'mejor': mejor,
        'peor': peor,
        'promedio': stats['promedio'],
        'nivel_promedio': stats['nivel_promedio'],
        'diferencia': stats['promedio'] - promedio_anterior if promedio_anterior is not None else None,
        'mes_comparado': MESES[anterior_mes - 1].lower(),
        'total_cumplidos': stats['total_cumplidos'],
        'dias_activos': stats['dias_activos'],
        'dias_del_mes': stats['dias_del_mes'],
        'dias_perfectos': sum(1 for d in con_pct if d['pct'] == 100),
        'mejor_racha': _mejor_racha(dias),
        'mejor_dia': f"{mejor_dia['numero']} de {nombre}" if mejor_dia and mejor_dia['hechos'] else None,
        'grafica': {'dias': [d['numero'] for d in dias], 'pct': [d['pct'] for d in dias]},
    }


def resumen_pendiente(idUser, hoy=None):
    """El resumen del mes pasado, si todavía no se le ha mostrado al usuario."""
    hoy = hoy or date.today()
    anio, mes = mes_anterior(hoy)
    if ResumenVisto.query.filter_by(idUser=idUser, anio=anio, mes=mes).first():
        return None
    return resumen_del_mes(idUser, anio, mes, hoy)


def marcar_resumen_visto(idUser, hoy=None):
    """No hace commit: lo hace quien llama."""
    anio, mes = mes_anterior(hoy or date.today())
    if not ResumenVisto.query.filter_by(idUser=idUser, anio=anio, mes=mes).first():
        db.session.add(ResumenVisto(idUser=idUser, anio=anio, mes=mes))
