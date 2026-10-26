"""Lógica de la sección Inglés: fondo animado y rangos de vocabulario."""
from app.models.vocabulario import Vocabulario


def get_letras_flotantes(id_user):
    """Palabras del usuario para el fondo animado de la sección Inglés.
    Si aún no tiene vocabulario agregado, usa un set genérico por defecto."""
    nombres = [p.nombre for p in Vocabulario.query.filter_by(idUser=id_user).all()]
    if not nombres:
        nombres = ['Hello', 'ABC', 'Learn', 'Yes', 'Go', 'Book', 'Fast', 'Easy', 'Words', 'English']

    letras = []
    i = 0
    while len(letras) < 10:
        letras.append(nombres[i % len(nombres)])
        i += 1
    return letras


# Rangos por cantidad de palabras agregadas, escalados hacia una meta real de 3,650 palabras
RANGOS_VOCABULARIO = [
    {'nombre': 'Novato', 'emoji': '🐣', 'umbral': 0},
    {'nombre': 'Aprendiz', 'emoji': '📖', 'umbral': 25},
    {'nombre': 'Explorador', 'emoji': '🧭', 'umbral': 75},
    {'nombre': 'Constante', 'emoji': '🔥', 'umbral': 150},
    {'nombre': 'Avanzado', 'emoji': '🚀', 'umbral': 300},
    {'nombre': 'Experto', 'emoji': '🎓', 'umbral': 600},
    {'nombre': 'Maestro', 'emoji': '🏆', 'umbral': 1000},
    {'nombre': 'Virtuoso', 'emoji': '💎', 'umbral': 1825},
    {'nombre': 'Políglota', 'emoji': '👑', 'umbral': 3650},
]

# Rangos por porcentaje de palabras dominadas (calificadas como "Fácil").
# Umbrales altos a propósito: este rango debe costar trabajo, no regalarse.
RANGOS_DOMINIO = [
    {'nombre': 'Principiante', 'emoji': '🌱', 'umbral': 0},
    {'nombre': 'En Progreso', 'emoji': '⚡', 'umbral': 35},
    {'nombre': 'Competente', 'emoji': '🎯', 'umbral': 60},
    {'nombre': 'Fluido', 'emoji': '🌟', 'umbral': 85},
    {'nombre': 'Dominado', 'emoji': '💯', 'umbral': 98},
]

# Palabras distintas que debes tener calificadas antes de que el % de dominio cuente de verdad
MINIMO_CALIFICACIONES_DOMINIO = 10

def calcular_rango(valor, tiers):
    rango_actual = tiers[0]
    siguiente = None
    for i, r in enumerate(tiers):
        if valor >= r['umbral']:
            rango_actual = r
            siguiente = tiers[i + 1] if i + 1 < len(tiers) else None

    if siguiente:
        base = rango_actual['umbral']
        meta = siguiente['umbral']
        pct_progreso = round(((valor - base) / (meta - base)) * 100)
        faltan = round(meta - valor, 1)
    else:
        pct_progreso = 100
        faltan = 0

    return rango_actual, siguiente, pct_progreso, faltan
