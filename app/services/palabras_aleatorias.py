"""Palabras aleatorias en inglés para practicar haciendo frases, sacadas del vocabulario del usuario."""
import random

from app.models.vocabulario import Vocabulario

MINIMO_PALABRAS = 1
MAXIMO_PALABRAS = 50
CANTIDAD_POR_DEFECTO = 5


def normalizar_cantidad(valor):
    """Convierte lo que escribió el usuario en una cantidad válida (entre el mínimo y el máximo).
    Devuelve None si no es un número."""
    try:
        cantidad = int(valor)
    except (TypeError, ValueError):
        return None
    return max(MINIMO_PALABRAS, min(MAXIMO_PALABRAS, cantidad))


def palabras_aleatorias(id_user, cantidad):
    """Elige hasta `cantidad` palabras distintas al azar del vocabulario del usuario."""
    vocabulario = Vocabulario.query.filter_by(idUser=id_user).all()
    # Una palabra guardada dos veces cuenta una sola vez
    unicas = list({v.nombre.strip().lower(): v for v in vocabulario}.values())
    elegidas = random.sample(unicas, min(cantidad, len(unicas)))
    return [{'palabra': v.nombre, 'significado': v.significado} for v in elegidas]


def total_vocabulario(id_user):
    """Cuántas palabras distintas tiene el usuario para practicar."""
    nombres = Vocabulario.query.with_entities(Vocabulario.nombre).filter_by(idUser=id_user).all()
    return len({nombre.strip().lower() for (nombre,) in nombres})
