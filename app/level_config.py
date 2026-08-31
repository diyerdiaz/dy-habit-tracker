"""Configuración y lógica pura del sistema de niveles (10 niveles máx.)."""

NIVEL_MAXIMO = 10
XP_POR_HABITO = 15
XP_BONUS_RACHA_SEMANAL = 20        # bono extra cada 7 días de racha consecutiva
PENALIZACION_POR_DIA_PERDIDO = 20  # XP que se resta por cada día sin actividad

NIVELES = [
    {'nivel': 1,  'titulo': 'Novato',               'umbral': 0},
    {'nivel': 2,  'titulo': 'Aprendiz',              'umbral': 100},
    {'nivel': 3,  'titulo': 'Constante',             'umbral': 300},
    {'nivel': 4,  'titulo': 'Disciplinado',          'umbral': 600},
    {'nivel': 5,  'titulo': 'Enfocado',              'umbral': 1000},
    {'nivel': 6,  'titulo': 'Resiliente',            'umbral': 1500},
    {'nivel': 7,  'titulo': 'Estratega',             'umbral': 2100},
    {'nivel': 8,  'titulo': 'Maestro de Hábitos',    'umbral': 2800},
    {'nivel': 9,  'titulo': 'Mentor de Disciplina',  'umbral': 3600},
    {'nivel': 10, 'titulo': 'Leyenda del Hábito',    'umbral': 4500},
]


def info_nivel_por_xp(xp):
    """Devuelve el dict de NIVELES correspondiente a una XP total dada."""
    actual = NIVELES[0]
    for n in NIVELES:
        if xp >= n['umbral']:
            actual = n
        else:
            break
    return actual


def calcular_progreso(xp):
    """
    A partir de la XP total, calcula:
    - nivel actual y título
    - xp acumulada dentro del nivel en curso
    - xp que falta para el siguiente nivel (0 si ya es nivel máximo)
    - % de progreso de la barra
    """
    xp = max(0, xp)
    actual = info_nivel_por_xp(xp)
    idx = actual['nivel'] - 1
    xp_en_nivel = xp - actual['umbral']

    if actual['nivel'] >= NIVEL_MAXIMO:
        return {
            'nivel': actual['nivel'],
            'titulo': actual['titulo'],
            'xp_en_nivel': xp_en_nivel,
            'xp_por_nivel': xp_en_nivel,
            'xp_para_subir': 0,
            'pct_nivel': 100,
            'es_nivel_maximo': True,
        }

    siguiente = NIVELES[idx + 1]
    xp_por_nivel = siguiente['umbral'] - actual['umbral']
    pct = round(xp_en_nivel / xp_por_nivel * 100)

    return {
        'nivel': actual['nivel'],
        'titulo': actual['titulo'],
        'xp_en_nivel': xp_en_nivel,
        'xp_por_nivel': xp_por_nivel,
        'xp_para_subir': siguiente['umbral'] - xp,
        'pct_nivel': pct,
        'es_nivel_maximo': False,
    }
