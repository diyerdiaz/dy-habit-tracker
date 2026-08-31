"""Lógica de mutación del progreso de gamificación (XP, racha, penalizaciones)."""

from datetime import date, timedelta
from app import db
from app.models.hist_habits import HistHabit
from app.models.user_progress import UserProgress
from app.level_config import XP_POR_HABITO, XP_BONUS_RACHA_SEMANAL, PENALIZACION_POR_DIA_PERDIDO


def get_or_create_progress(idUser):
    progress = UserProgress.query.get(idUser)
    if not progress:
        progress = UserProgress(idUser=idUser)
        db.session.add(progress)
        db.session.flush()
    return progress


def calcular_racha(idUser):
    """Racha actual y máxima, derivadas de los días con al menos un hábito marcado."""
    dias = sorted({h.fecha for h in HistHabit.query.filter_by(idUser=idUser).all()})
    if not dias:
        return 0, 0

    racha_maxima = racha_temp = 0
    for i, dia in enumerate(dias):
        if i == 0 or (dia - dias[i - 1]).days == 1:
            racha_temp += 1
            racha_maxima = max(racha_maxima, racha_temp)
        else:
            racha_temp = 1

    racha_actual = 0
    hoy = date.today()
    ultimo_dia = dias[-1]
    if (hoy - ultimo_dia).days <= 1:
        dias_set = set(dias)
        cursor = ultimo_dia
        while cursor in dias_set:
            racha_actual += 1
            cursor -= timedelta(days=1)

    return racha_actual, racha_maxima


def aplicar_penalizaciones_pendientes(progress):
    """
    Resta XP por cada día completo transcurrido sin actividad desde la última
    vez que se revisó. Se apoya en `ultimaFechaPenalizada` para no penalizar
    el mismo día dos veces, y en HistHabit para saber qué días sí tuvieron actividad.
    """
    if not progress.ultimaFechaActividad:
        return False

    hoy = date.today()
    dias_con_actividad = {
        h.fecha for h in HistHabit.query.filter_by(idUser=progress.idUser).all()
    }

    cursor = (progress.ultimaFechaPenalizada or progress.ultimaFechaActividad) + timedelta(days=1)
    penalizado = False
    while cursor < hoy:
        if cursor not in dias_con_actividad:
            progress.xpTotal = max(0, progress.xpTotal - PENALIZACION_POR_DIA_PERDIDO)
            penalizado = True
        progress.ultimaFechaPenalizada = cursor
        cursor += timedelta(days=1)

    return penalizado


def sincronizar_racha(progress):
    racha_actual, racha_maxima = calcular_racha(progress.idUser)
    progress.rachaActual = racha_actual
    progress.rachaMaxima = max(progress.rachaMaxima, racha_maxima)
    return racha_actual, racha_maxima


def registrar_toggle_habito(idUser, marcado_como_hecho):
    """
    Actualiza XP y contadores cuando se marca/desmarca un hábito como hecho hoy.
    Debe llamarse DESPUÉS de crear/eliminar el registro correspondiente en HistHabit.
    """
    progress = get_or_create_progress(idUser)
    aplicar_penalizaciones_pendientes(progress)

    racha_previa = progress.rachaActual

    if marcado_como_hecho:
        progress.xpTotal += XP_POR_HABITO
        progress.habitosCompletados += 1
    else:
        progress.xpTotal = max(0, progress.xpTotal - XP_POR_HABITO)
        progress.habitosCompletados = max(0, progress.habitosCompletados - 1)

    racha_actual, _ = sincronizar_racha(progress)

    # Bono semanal: al alcanzar un múltiplo de 7 en la racha (y no antes ya lo tenía)
    if marcado_como_hecho and racha_actual > racha_previa and racha_actual % 7 == 0:
        progress.xpTotal += XP_BONUS_RACHA_SEMANAL

    progress.ultimaFechaActividad = date.today()
    db.session.commit()
    return progress
