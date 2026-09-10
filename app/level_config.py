"""Configuración y lógica pura del sistema de niveles (10 niveles máx.)."""

NIVEL_MAXIMO = 10
XP_POR_HABITO = 15
XP_BONUS_RACHA_SEMANAL = 20        # bono extra cada 7 días de racha consecutiva
PENALIZACION_POR_DIA_PERDIDO = 20  # XP que se resta por cada día sin actividad

NIVELES = [
    {'nivel': 1,  'titulo': 'Novato',               'umbral': 0},
    {'nivel': 2,  'titulo': 'Aprendiz',              'umbral': 500},
    {'nivel': 3,  'titulo': 'Constante',             'umbral': 1500},
    {'nivel': 4,  'titulo': 'Disciplinado',          'umbral': 3000},
    {'nivel': 5,  'titulo': 'Enfocado',              'umbral': 5000},
    {'nivel': 6,  'titulo': 'Resiliente',            'umbral': 7500},
    {'nivel': 7,  'titulo': 'Estratega',             'umbral': 10500},
    {'nivel': 8,  'titulo': 'Maestro de Hábitos',    'umbral': 14000},
    {'nivel': 9,  'titulo': 'Mentor de Disciplina',  'umbral': 18000},
    {'nivel': 10, 'titulo': 'Leyenda del Hábito',    'umbral': 22500},
]
# Umbral(N) = 500 * (N-1) * N / 2 -> a ~4 hábitos/día (60 XP/día) llegar al
# nivel 10 toma unos 375 días (~1 año) completando de forma constante.


def info_nivel_por_xp(xp):
    """Devuelve el dict de NIVELES correspondiente a una XP total dada."""
    actual = NIVELES[0]
    for n in NIVELES:
        if xp >= n['umbral']:
            actual = n
        else:
            break
    return actual


def nivel_maximo_por_habitos(cantidad_habitos):
    """
    Tope de nivel según hábitos DISTINTOS creados (no completados):
    el nivel N exige al menos N hábitos registrados en 'Gestión de Hábitos'.
    Aunque sobre XP, no se puede pasar de este tope.
    """
    if cantidad_habitos <= 0:
        return 1
    return min(NIVEL_MAXIMO, cantidad_habitos)


def calcular_progreso(xp, cantidad_habitos=0):
    """
    A partir de la XP total y de cuántos hábitos distintos tiene creados
    el usuario, calcula el nivel real (limitado por ambos requisitos),
    cuánta XP falta y cuántos hábitos nuevos hay que crear para el siguiente
    nivel, y si el usuario está "tapado" por falta de hábitos aunque le
    sobre XP.
    """
    xp = max(0, xp)
    nivel_por_xp = info_nivel_por_xp(xp)['nivel']
    tope_por_habitos = nivel_maximo_por_habitos(cantidad_habitos)

    nivel_real = min(nivel_por_xp, tope_por_habitos)
    bloqueado_por_habitos = nivel_por_xp > tope_por_habitos

    actual = NIVELES[nivel_real - 1]
    idx = nivel_real - 1
    xp_en_nivel = xp - actual['umbral']

    if nivel_real >= NIVEL_MAXIMO:
        return {
            'nivel': nivel_real,
            'titulo': actual['titulo'],
            'xp_en_nivel': xp_en_nivel,
            'xp_por_nivel': xp_en_nivel,
            'xp_para_subir': 0,
            'habitos_para_subir': 0,
            'pct_nivel': 100,
            'es_nivel_maximo': True,
            'bloqueado_por_habitos': False,
        }

    siguiente = NIVELES[idx + 1]
    xp_por_nivel = siguiente['umbral'] - actual['umbral']

    if bloqueado_por_habitos:
        # Ya alcanzó (o superó) la XP de este nivel; se muestra la barra
        # llena en vez de pasarse, ya que lo único que falta son hábitos.
        xp_en_nivel = min(xp_en_nivel, xp_por_nivel)

    pct = round(xp_en_nivel / xp_por_nivel * 100) if xp_por_nivel else 100

    return {
        'nivel': nivel_real,
        'titulo': actual['titulo'],
        'xp_en_nivel': xp_en_nivel,
        'xp_por_nivel': xp_por_nivel,
        'xp_para_subir': max(0, siguiente['umbral'] - xp),
        'habitos_para_subir': max(0, siguiente['nivel'] - cantidad_habitos),
        'pct_nivel': pct,
        'es_nivel_maximo': False,
        'bloqueado_por_habitos': bloqueado_por_habitos,
    }
