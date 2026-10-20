"""Lógica de mutación del progreso de gamificación (XP, racha, penalizaciones)."""

from datetime import date, timedelta
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.user_progress import UserProgress
from app.level_config import XP_POR_HABITO, XP_BONUS_RACHA_SEMANAL, PENALIZACION_POR_DIA_PERDIDO


def get_or_create_progress(idUser):
    progress = db.session.get(UserProgress, idUser)
    if not progress:
        progress = UserProgress(idUser=idUser)
        db.session.add(progress)
        db.session.flush()
    return progress


def dias_programados(idUser):
    """Días de la semana (0-6) en que el usuario tiene al menos un hábito activo.
    Los días que no aparecen aquí son de descanso: no rompen la racha ni restan XP."""
    dias = set()
    for habit in Habit.query.filter_by(idUser=idUser, habitState='Activo').all():
        dias.update(habit.dias_lista())
    return dias


def calcular_racha(idUser):
    """Racha actual y máxima, derivadas de los días con al menos un hábito marcado.
    Los días de descanso (sin hábitos programados) no cortan la racha."""
    dias = {h.fecha for h in HistHabit.query.filter_by(idUser=idUser).all()}
    if not dias:
        return 0, 0

    programados = dias_programados(idUser)
    hoy = date.today()
    racha_maxima = racha_temp = 0
    cursor = min(dias)
    while cursor <= hoy:
        if cursor in dias:
            racha_temp += 1
            racha_maxima = max(racha_maxima, racha_temp)
        elif cursor != hoy and cursor.weekday() in programados:
            # Día que tocaba y no se hizo nada. Hoy aún no cuenta: queda tiempo.
            racha_temp = 0
        cursor += timedelta(days=1)

    return racha_temp, racha_maxima


def aplicar_penalizaciones_pendientes(progress):
    """
    Resta XP por cada día completo transcurrido sin actividad desde la última
    vez que se revisó. Se apoya en `ultimaFechaPenalizada` para no penalizar
    el mismo día dos veces, y en HistHabit para saber qué días sí tuvieron actividad.
    Los días de descanso (sin hábitos programados) nunca restan XP.
    """
    if not progress.ultimaFechaActividad:
        return False

    hoy = date.today()
    dias_con_actividad = {
        h.fecha for h in HistHabit.query.filter_by(idUser=progress.idUser).all()
    }
    programados = dias_programados(progress.idUser)

    cursor = (progress.ultimaFechaPenalizada or progress.ultimaFechaActividad) + timedelta(days=1)
    penalizado = False
    while cursor < hoy:
        if cursor not in dias_con_actividad and cursor.weekday() in programados:
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


def registrar_recuperacion(idUser):
    """
    Recalcula la racha después de recuperar un día perdido (el día ya tiene su
    registro en HistHabit). Recuperar no da XP ni devuelve penalizaciones:
    solo salva el día y la racha.
    Debe llamarse DESPUÉS de crear el registro en HistHabit.
    """
    progress = get_or_create_progress(idUser)
    aplicar_penalizaciones_pendientes(progress)
    sincronizar_racha(progress)
    db.session.commit()
    return progress
