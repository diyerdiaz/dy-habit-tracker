"""Lógica de la sección Inglés: fondo animado, rangos de vocabulario y resumen del dashboard."""
import random
from datetime import date, timedelta

from app import db
from app.models.juego_partida import JuegoPartida
from app.models.shadowing_sesion import ShadowingSesion
from app.models.vocabulario import Vocabulario
from app.models.vocabulario_registro import VocabularioRegistro
from app.services.secciones import INGLES, SECCIONES


def get_letras_flotantes(id_user, idioma=INGLES):
    """Palabras del usuario para el fondo animado de la sección (Inglés o Español),
    elegidas al azar en cada visita. Sin vocabulario agregado usa un set por defecto."""
    nombres = list({nombre for (nombre,) in db.session.query(Vocabulario.nombre)
                    .filter_by(idUser=id_user, idioma=idioma)})
    if not nombres:
        nombres = list(SECCIONES[idioma]['palabras_fondo'])

    if len(nombres) >= 10:
        return random.sample(nombres, 10)
    # Con menos de 10 palabras se repiten, pero en orden revuelto
    letras = nombres * (10 // len(nombres) + 1)
    random.shuffle(letras)
    return letras[:10]


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

# Español tiene su propia escalera, con nombres de las letras (mismos umbrales que Inglés)
RANGOS_VOCABULARIO_ES = [
    {'nombre': 'Pluma Naciente', 'emoji': '🪶', 'umbral': 0},
    {'nombre': 'Lector Curioso', 'emoji': '📜', 'umbral': 25},
    {'nombre': 'Cronista', 'emoji': '✒️', 'umbral': 75},
    {'nombre': 'Narrador', 'emoji': '📚', 'umbral': 150},
    {'nombre': 'Poeta', 'emoji': '🌹', 'umbral': 300},
    {'nombre': 'Erudito', 'emoji': '🦉', 'umbral': 600},
    {'nombre': 'Maestro de la Prosa', 'emoji': '🖋️', 'umbral': 1000},
    {'nombre': 'Académico de la Lengua', 'emoji': '🏛️', 'umbral': 1825},
    {'nombre': 'Alma de Cervantes', 'emoji': '👑', 'umbral': 3650},
]

RANGOS_DOMINIO_ES = [
    {'nombre': 'Primer Borrador', 'emoji': '📝', 'umbral': 0},
    {'nombre': 'Verso Libre', 'emoji': '🍃', 'umbral': 35},
    {'nombre': 'Prosa Clara', 'emoji': '💡', 'umbral': 60},
    {'nombre': 'Pluma Elegante', 'emoji': '🌟', 'umbral': 85},
    {'nombre': 'Palabra Maestra', 'emoji': '💎', 'umbral': 98},
]


def rangos_vocabulario(idioma=INGLES):
    """Escalera de rangos por palabras agregadas de cada idioma."""
    return RANGOS_VOCABULARIO_ES if idioma == 'es' else RANGOS_VOCABULARIO


def rangos_dominio(idioma=INGLES):
    """Escalera de rangos por % de palabras dominadas de cada idioma."""
    return RANGOS_DOMINIO_ES if idioma == 'es' else RANGOS_DOMINIO


# Palabras distintas que debes tener calificadas antes de que el % de dominio cuente de verdad
MINIMO_CALIFICACIONES_DOMINIO = 10

# Tiempo mínimo (segundos) que hay que quedarse en cada tarjeta antes de poder
# calificarla y pasar a la siguiente. 0 = sin mínimo.
TIEMPOS_TARJETA = [0, 5, 10, 15, 20, 30, 45, 60]
TIEMPO_TARJETA_POR_DEFECTO = 10

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


DIAS_CORTOS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
DIAS_GRAFICA = 30     # "Día a día": los últimos 30 días
MESES_GRAFICA = 12    # "Mes a mes": los últimos 12 meses
ANIOS_MINIMOS = 3     # "Año a año": al menos los últimos 3 años, aunque estén vacíos


def _actividad(id_user, idioma=INGLES):
    """Fechas de todo lo practicado en la sección: palabras agregadas, repasos,
    sesiones de shadowing (con sus segundos, solo en Inglés) y partidas de juegos."""
    palabras = [f.date() for (f,) in db.session.query(Vocabulario.createdAt)
                .filter_by(idUser=id_user, idioma=idioma) if f]
    repasos = [f.date() for (f,) in db.session.query(VocabularioRegistro.fecha)
               .filter_by(idUser=id_user, idioma=idioma) if f]
    shadowing = []
    if idioma == INGLES:
        shadowing = [(f.date(), s) for f, s in db.session.query(ShadowingSesion.fecha, ShadowingSesion.duracionSegundos)
                     .filter_by(idUser=id_user) if f]
    juegos = [f.date() for (f,) in db.session.query(JuegoPartida.fecha)
              .filter_by(idUser=id_user, idioma=idioma) if f]
    return palabras, repasos, shadowing, juegos


def _racha(dias_activos, hoy):
    """Días seguidos con práctica. Si hoy aún no practica, la racha de ayer sigue viva."""
    dia = hoy if hoy in dias_activos else hoy - timedelta(days=1)
    racha = 0
    while dia in dias_activos:
        racha += 1
        dia -= timedelta(days=1)
    return racha


def resumen_ingles(id_user, hoy=None, idioma=INGLES):
    """Números del dashboard de Inglés: palabras, repasos, shadowing, juegos y racha.
    Cuenta como día practicado agregar o repasar una palabra, hacer shadowing o jugar."""
    hoy = hoy or date.today()
    hace_7 = hoy - timedelta(days=6)
    palabras, repasos, shadowing, juegos = _actividad(id_user, idioma)

    dias_activos = set(palabras) | set(repasos) | {d for d, _ in shadowing} | set(juegos)
    rango, siguiente, pct_rango, faltan = calcular_rango(len(palabras), rangos_vocabulario(idioma))

    semana = []
    for i in range(7):
        dia = hace_7 + timedelta(days=i)
        semana.append({
            'letra': DIAS_CORTOS[dia.weekday()],
            'numero': dia.day,
            'activo': dia in dias_activos,
            'hoy': dia == hoy,
        })

    return {
        'palabras_total': len(palabras),
        'palabras_semana': sum(1 for d in palabras if d >= hace_7),
        'repasos_hoy': sum(1 for d in repasos if d == hoy),
        'repasos_total': len(repasos),
        'minutos_shadowing_total': sum(s for _, s in shadowing) // 60,
        'minutos_shadowing_semana': sum(s for d, s in shadowing if d >= hace_7) // 60,
        'partidas_total': len(juegos),
        'racha': _racha(dias_activos, hoy),
        'practico_hoy': hoy in dias_activos,
        'semana': semana,
        'rango': rango,
        'siguiente_rango': siguiente,
        'pct_rango': pct_rango,
        'faltan_rango': faltan,
    }


def _serie(claves, clave_de, palabras, repasos, shadowing, juegos):
    """Suma la actividad en cada periodo (`claves`); `clave_de(fecha)` dice a cuál pertenece una fecha."""
    indice = {k: i for i, k in enumerate(claves)}
    serie = {nombre: [0] * len(claves) for nombre in ('palabras', 'repasos', 'partidas', 'segundos')}
    for nombre, fechas in (('palabras', palabras), ('repasos', repasos), ('partidas', juegos)):
        for f in fechas:
            i = indice.get(clave_de(f))
            if i is not None:
                serie[nombre][i] += 1
    for f, segundos in shadowing:
        i = indice.get(clave_de(f))
        if i is not None:
            serie['segundos'][i] += segundos
    serie['minutos'] = [round(s / 60) for s in serie.pop('segundos')]
    return serie


def graficas_ingles(id_user, hoy=None, idioma=INGLES):
    """Datos de las gráficas de rendimiento del dashboard de Inglés:
    día a día (últimos 30 días), mes a mes (últimos 12 meses) y año a año."""
    hoy = hoy or date.today()
    actividad = _actividad(id_user, idioma)

    dias = [hoy - timedelta(days=i) for i in range(DIAS_GRAFICA - 1, -1, -1)]

    meses = []
    anio, mes = hoy.year, hoy.month
    for _ in range(MESES_GRAFICA):
        meses.append((anio, mes))
        anio, mes = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
    meses.reverse()

    todas = actividad[0] + actividad[1] + [f for f, _ in actividad[2]] + actividad[3]
    primer_anio = min([f.year for f in todas] + [hoy.year - ANIOS_MINIMOS + 1])
    anios = list(range(primer_anio, hoy.year + 1))

    return {
        'dia': {'etiquetas': [f'{d.day} {MESES_CORTOS[d.month - 1]}' for d in dias],
                **_serie(dias, lambda f: f, *actividad)},
        'mes': {'etiquetas': [f'{MESES_CORTOS[m - 1]} {a}' for a, m in meses],
                **_serie(meses, lambda f: (f.year, f.month), *actividad)},
        'anio': {'etiquetas': [str(a) for a in anios],
                 **_serie(anios, lambda f: f.year, *actividad)},
    }
