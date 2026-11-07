"""Retos con XP apostado: el admin los crea, el usuario los acepta o rechaza y,
si acepta, marca "Cumplí hoy" cada día. Todos los días cumplidos = gana la
apuesta; un día sin marcar = la pierde."""

from datetime import date, datetime, timedelta

from app import db
from app.models.retos import (
    Reto, RetoDia, PENDIENTE, EN_CURSO, GANADO, PERDIDO, RECHAZADO, VENCIDO, CANCELADO,
    ABIERTOS, CERRADOS_CON_RESULTADO,
)
from app.services.gamificacion import get_or_create_progress

MAX_NOMBRE = 120
MAX_DESCRIPCION = 500
MAX_DIAS = 90
MAX_APUESTA = 10000


def validar_reto(nombre, descripcion, inicio, fin, apuesta, hoy=None, todo=False):
    """Devuelve el mensaje de error del formulario del admin, o None si todo está bien."""
    hoy = hoy or date.today()
    if not nombre:
        return 'Escribe el nombre del reto.'
    if len(nombre) > MAX_NOMBRE or len(descripcion or '') > MAX_DESCRIPCION:
        return f'El nombre admite {MAX_NOMBRE} caracteres y la descripción {MAX_DESCRIPCION}.'
    if inicio is None or fin is None:
        return 'Elige la fecha de inicio y la de fin.'
    if inicio < hoy:
        return 'El reto no puede empezar en un día que ya pasó.'
    if fin < inicio:
        return 'La fecha de fin debe ser igual o posterior a la de inicio.'
    if (fin - inicio).days + 1 > MAX_DIAS:
        return f'Un reto dura como máximo {MAX_DIAS} días.'
    if not todo and (apuesta is None or not 0 <= apuesta <= MAX_APUESTA):
        return f'La apuesta va de 0 a {MAX_APUESTA} XP.'
    return None


def crear_reto(user, nombre, descripcion, inicio, fin, apuesta, todo=False):
    """Con `todo` la apuesta es todo el XP que tenga el usuario al aceptar."""
    reto = Reto(idUser=user.idUser, nombre=nombre, descripcion=descripcion or None,
                fechaInicio=inicio, fechaFin=fin, apuesta=0 if todo else apuesta, todoXp=todo)
    db.session.add(reto)
    db.session.commit()
    return reto


def dias_cumplidos(reto):
    return {d.fecha for d in reto.dias}


def _cerrar(reto, estado):
    reto.estado = estado
    reto.cerradoEn = datetime.now()
    if estado in CERRADOS_CON_RESULTADO and reto.apuesta:
        progreso = get_or_create_progress(reto.idUser)
        signo = 1 if estado == GANADO else -1
        progreso.xpTotal = max(0, progreso.xpTotal + signo * reto.apuesta)


def actualizar_reto(reto, hoy=None):
    """Cierra el reto si ya se sabe cómo terminó. No hace commit. True si cambió.
    - Pendiente y ya pasó el día de inicio sin respuesta: vence (sin perder nada).
    - En curso y quedó un día pasado sin marcar: perdido (resta la apuesta).
    - En curso y se marcaron todos sus días: ganado (suma la apuesta)."""
    hoy = hoy or date.today()
    if reto.estado == PENDIENTE and hoy > reto.fechaInicio:
        _cerrar(reto, VENCIDO)
        return True
    if reto.estado != EN_CURSO:
        return False
    hechos = dias_cumplidos(reto)
    dia = reto.fechaInicio
    while dia <= reto.fechaFin and dia < hoy:
        if dia not in hechos:
            _cerrar(reto, PERDIDO)
            return True
        dia += timedelta(days=1)
    if len(hechos) >= reto.total_dias():
        _cerrar(reto, GANADO)
        return True
    return False


def actualizar_retos(idUser, hoy=None):
    """Revisa todos los retos abiertos del usuario y guarda si alguno terminó."""
    cambio = False
    for reto in Reto.query.filter(Reto.idUser == idUser, Reto.estado.in_(ABIERTOS)).all():
        cambio = actualizar_reto(reto, hoy) or cambio
    if cambio:
        db.session.commit()


def retos_del_usuario(idUser, hoy=None):
    """Sus retos, revisados al día: primero los abiertos y luego el historial."""
    actualizar_retos(idUser, hoy)
    retos = Reto.query.filter(Reto.idUser == idUser, Reto.estado.notin_((RECHAZADO,))) \
        .order_by(Reto.fechaInicio.desc(), Reto.idReto.desc()).all()
    return sorted(retos, key=lambda r: r.estado not in ABIERTOS)


def retos_para_admin(idUser, hoy=None):
    """Todos sus retos (también los rechazados), revisados al día, con su resumen."""
    actualizar_retos(idUser, hoy)
    retos = Reto.query.filter_by(idUser=idUser).order_by(Reto.fechaInicio.desc(), Reto.idReto.desc()).all()
    return [resumen_reto(r, hoy) for r in retos]


def mostrar_en_menu(idUser, hoy=None):
    """El botón "Retos" aparece si tiene uno por responder o en curso, o uno que
    ganó o perdió y todavía no ha visto. Si rechaza el único, desaparece."""
    actualizar_retos(idUser, hoy)
    return db.session.query(Reto.idReto).filter(
        Reto.idUser == idUser,
        db.or_(Reto.estado.in_(ABIERTOS),
               db.and_(Reto.estado.in_(CERRADOS_CON_RESULTADO), Reto.resultadoVisto.is_(False))),
    ).first() is not None


def marcar_resultados_vistos(retos):
    vistos = [r for r in retos if r.estado in CERRADOS_CON_RESULTADO and not r.resultadoVisto]
    for reto in vistos:
        reto.resultadoVisto = True
    if vistos:
        db.session.commit()


def responder(reto, acepta, hoy=None):
    """El usuario acepta o rechaza. Solo se puede hasta el día de inicio.
    Devuelve el mensaje de error o None."""
    actualizar_reto(reto, hoy)
    if reto.estado != PENDIENTE:
        db.session.commit()
        return 'Este reto ya no espera respuesta.'
    reto.estado = EN_CURSO if acepta else RECHAZADO
    if acepta and reto.todoXp:
        # Todo o nada: queda en juego todo el XP que tiene en este momento
        reto.apuesta = get_or_create_progress(reto.idUser).xpTotal
    if not acepta:
        reto.cerradoEn = datetime.now()
    db.session.commit()
    return None


def cumplir_hoy(reto, hoy=None):
    """Marca o desmarca "Cumplí hoy". Devuelve (marcado, error)."""
    hoy = hoy or date.today()
    actualizar_reto(reto, hoy)
    if reto.estado != EN_CURSO:
        db.session.commit()
        return False, 'Este reto ya terminó.'
    if not reto.fechaInicio <= hoy <= reto.fechaFin:
        return False, f'El reto empieza el {reto.fechaInicio.strftime("%d/%m/%Y")}.'
    registro = reto.dias.filter_by(fecha=hoy).first()
    if registro:
        db.session.delete(registro)
    else:
        db.session.add(RetoDia(idReto=reto.idReto, idUser=reto.idUser, fecha=hoy))
    db.session.flush()
    actualizar_reto(reto, hoy)   # si era el último día, lo gana en ese momento
    db.session.commit()
    return registro is None, None


def cancelar(reto):
    """El admin cancela un reto abierto: nadie gana ni pierde XP."""
    if reto.estado not in ABIERTOS:
        return False
    _cerrar(reto, CANCELADO)
    db.session.commit()
    return True


def resumen_reto(reto, hoy=None):
    """Datos para mostrar la tarjeta del reto."""
    hoy = hoy or date.today()
    hechos = dias_cumplidos(reto)
    dias = [(reto.fechaInicio + timedelta(days=i)) for i in range(reto.total_dias())]
    return {
        'reto': reto,
        'dias': [(d, d in hechos, d == hoy) for d in dias],
        'cumplidos': len(hechos),
        'total': reto.total_dias(),
        'hoy_marcado': hoy in hechos,
        'puede_marcar': reto.estado == EN_CURSO and reto.fechaInicio <= hoy <= reto.fechaFin,
        'falta_para_empezar': (reto.fechaInicio - hoy).days if hoy < reto.fechaInicio else 0,
    }
