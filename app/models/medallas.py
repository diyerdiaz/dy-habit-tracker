"""Catálogo de medallas (30 básicas + 100 de rango) y cálculo del progreso de cada una.

Las medallas no se guardan en la base de datos: se calculan al vuelo a partir
de la actividad del usuario, así nunca quedan desincronizadas.
"""

from datetime import date
from sqlalchemy import func
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.tareas import Tarea
from app.models.vocabulario import Vocabulario
from app.models.vocabulario_registro import VocabularioRegistro
from app.models.shadowing_sesion import ShadowingSesion
from app.models.ruleta_castigo import Castigo
from app.models.metodo_estudio import MetodoEstudio, KanbanTarjeta, Apunte
from app.models.estadisticas import meses_disponibles, estadisticas_del_mes
from app.services.gamificacion import get_or_create_progress, sincronizar_racha
from app.services.level_config import calcular_progreso

CATEGORIAS = {
    'habitos':   {'nombre': 'Hábitos',    'icono': 'bi-check2-circle'},
    'racha':     {'nombre': 'Racha',      'icono': 'bi-fire'},
    'nivel':     {'nombre': 'Nivel',      'icono': 'bi-award'},
    'tareas':    {'nombre': 'Tareas',     'icono': 'bi-card-checklist'},
    'ingles':    {'nombre': 'Inglés',     'icono': 'bi-translate'},
    'estudio':   {'nombre': 'Estudio',    'icono': 'bi-kanban'},
    'especial':  {'nombre': 'Especiales', 'icono': 'bi-stars'},
}

# rareza: bronce, plata, oro, diamante (define el color de la tarjeta)
MEDALLAS = [
    # ── Hábitos completados ──
    {'id': 'primer_paso', 'nombre': 'Primer Paso', 'categoria': 'habitos', 'metrica': 'completados', 'meta': 1,
     'icono': 'bi-flag-fill', 'rareza': 'bronce',
     'descripcion': 'Completa tu primer hábito.',
     'frase': 'Todo gran viaje empieza con un solo paso.'},
    {'id': 'en_marcha', 'nombre': 'En Marcha', 'categoria': 'habitos', 'metrica': 'completados', 'meta': 10,
     'icono': 'bi-play-circle-fill', 'rareza': 'bronce',
     'descripcion': 'Completa 10 hábitos.',
     'frase': 'Ya arrancaste. Ahora nadie te detiene.'},
    {'id': 'cuarto_de_cien', 'nombre': 'Cuarto de Cien', 'categoria': 'habitos', 'metrica': 'completados', 'meta': 25,
     'icono': 'bi-pie-chart-fill', 'rareza': 'plata',
     'descripcion': 'Completa 25 hábitos.',
     'frase': 'La constancia está empezando a notarse.'},
    {'id': 'medio_centenar', 'nombre': 'Medio Centenar', 'categoria': 'habitos', 'metrica': 'completados', 'meta': 50,
     'icono': 'bi-bullseye', 'rareza': 'plata',
     'descripcion': 'Completa 50 hábitos.',
     'frase': 'Cincuenta veces elegiste mejorar. Eso es carácter.'},
    {'id': 'centurion', 'nombre': 'Centurión', 'categoria': 'habitos', 'metrica': 'completados', 'meta': 100,
     'icono': 'bi-shield-fill-check', 'rareza': 'oro',
     'descripcion': 'Completa 100 hábitos.',
     'frase': 'Cien victorias pequeñas construyen una gran persona.'},
    {'id': 'imparable', 'nombre': 'Imparable', 'categoria': 'habitos', 'metrica': 'completados', 'meta': 250,
     'icono': 'bi-lightning-charge-fill', 'rareza': 'oro',
     'descripcion': 'Completa 250 hábitos.',
     'frase': 'Ya no es motivación, es disciplina.'},
    {'id': 'maquina_de_habitos', 'nombre': 'Máquina de Hábitos', 'categoria': 'habitos', 'metrica': 'completados', 'meta': 500,
     'icono': 'bi-gear-wide-connected', 'rareza': 'diamante',
     'descripcion': 'Completa 500 hábitos.',
     'frase': 'Te convertiste en la persona que querías ser.'},
    {'id': 'arquitecto', 'nombre': 'Arquitecto', 'categoria': 'habitos', 'metrica': 'creados', 'meta': 1,
     'icono': 'bi-pencil-square', 'rareza': 'bronce',
     'descripcion': 'Crea tu primer hábito.',
     'frase': 'Diseñar tu rutina es diseñar tu futuro.'},
    {'id': 'constructor', 'nombre': 'Constructor', 'categoria': 'habitos', 'metrica': 'creados', 'meta': 5,
     'icono': 'bi-bricks', 'rareza': 'plata',
     'descripcion': 'Crea 5 hábitos distintos.',
     'frase': 'Cada hábito es un ladrillo de tu mejor versión.'},
    {'id': 'visionario', 'nombre': 'Visionario', 'categoria': 'habitos', 'metrica': 'creados', 'meta': 10,
     'icono': 'bi-eye-fill', 'rareza': 'oro',
     'descripcion': 'Crea 10 hábitos distintos.',
     'frase': 'Ves más lejos porque te preparas más.'},

    # ── Racha ──
    {'id': 'chispa', 'nombre': 'Chispa', 'categoria': 'racha', 'metrica': 'racha_max', 'meta': 3,
     'icono': 'bi-fire', 'rareza': 'bronce',
     'descripcion': 'Logra una racha de 3 días seguidos.',
     'frase': 'Una chispa basta para encender un incendio.'},
    {'id': 'semana_perfecta', 'nombre': 'Semana Perfecta', 'categoria': 'racha', 'metrica': 'racha_max', 'meta': 7,
     'icono': 'bi-calendar-week-fill', 'rareza': 'plata',
     'descripcion': 'Logra una racha de 7 días seguidos.',
     'frase': 'Siete días sin fallar. Tu yo del futuro te lo agradece.'},
    {'id': 'quincena_de_hierro', 'nombre': 'Quincena de Hierro', 'categoria': 'racha', 'metrica': 'racha_max', 'meta': 14,
     'icono': 'bi-hammer', 'rareza': 'plata',
     'descripcion': 'Logra una racha de 14 días seguidos.',
     'frase': 'Dos semanas forjando tu voluntad.'},
    {'id': 'mes_de_fuego', 'nombre': 'Mes de Fuego', 'categoria': 'racha', 'metrica': 'racha_max', 'meta': 30,
     'icono': 'bi-calendar-heart-fill', 'rareza': 'oro',
     'descripcion': 'Logra una racha de 30 días seguidos.',
     'frase': 'Un mes entero: el hábito ya es parte de ti.'},
    {'id': 'inquebrantable', 'nombre': 'Inquebrantable', 'categoria': 'racha', 'metrica': 'racha_max', 'meta': 60,
     'icono': 'bi-gem', 'rareza': 'oro',
     'descripcion': 'Logra una racha de 60 días seguidos.',
     'frase': 'Nada ni nadie rompe tu compromiso.'},
    {'id': 'leyenda_de_la_racha', 'nombre': 'Leyenda de la Racha', 'categoria': 'racha', 'metrica': 'racha_max', 'meta': 100,
     'icono': 'bi-trophy-fill', 'rareza': 'diamante',
     'descripcion': 'Logra una racha de 100 días seguidos.',
     'frase': 'Cien días seguidos. Eres leyenda.'},
    {'id': 'veterano', 'nombre': 'Veterano', 'categoria': 'racha', 'metrica': 'dias_activos', 'meta': 50,
     'icono': 'bi-calendar-check-fill', 'rareza': 'oro',
     'descripcion': 'Acumula 50 días con al menos un hábito completado.',
     'frase': 'Aunque caigas, siempre vuelves. Eso es lo que cuenta.'},

    # ── Nivel ──
    {'id': 'subiendo', 'nombre': 'Subiendo', 'categoria': 'nivel', 'metrica': 'nivel', 'meta': 2,
     'icono': 'bi-graph-up-arrow', 'rareza': 'bronce',
     'descripcion': 'Alcanza el nivel 2.',
     'frase': 'El primer nivel es la prueba de que puedes.'},
    {'id': 'mitad_del_camino', 'nombre': 'Mitad del Camino', 'categoria': 'nivel', 'metrica': 'nivel', 'meta': 5,
     'icono': 'bi-signpost-split-fill', 'rareza': 'oro',
     'descripcion': 'Alcanza el nivel 5.',
     'frase': 'Ya recorriste la mitad. Lo mejor está por venir.'},
    {'id': 'cima', 'nombre': 'La Cima', 'categoria': 'nivel', 'metrica': 'nivel', 'meta': 10,
     'icono': 'bi-award-fill', 'rareza': 'diamante',
     'descripcion': 'Alcanza el nivel máximo (10).',
     'frase': 'Desde aquí arriba, todo el esfuerzo valió la pena.'},

    # ── Tareas ──
    {'id': 'tarea_cumplida', 'nombre': 'Tarea Cumplida', 'categoria': 'tareas', 'metrica': 'tareas', 'meta': 1,
     'icono': 'bi-check2-square', 'rareza': 'bronce',
     'descripcion': 'Completa tu primera tarea del día.',
     'frase': 'Lo que se termina, libera la mente.'},
    {'id': 'productivo', 'nombre': 'Productivo', 'categoria': 'tareas', 'metrica': 'tareas', 'meta': 25,
     'icono': 'bi-list-check', 'rareza': 'plata',
     'descripcion': 'Completa 25 tareas.',
     'frase': 'Menos excusas, más tachones en la lista.'},
    {'id': 'ejecutor', 'nombre': 'Ejecutor', 'categoria': 'tareas', 'metrica': 'tareas', 'meta': 100,
     'icono': 'bi-rocket-takeoff-fill', 'rareza': 'oro',
     'descripcion': 'Completa 100 tareas.',
     'frase': 'Planeas, ejecutas y cumples. Así se hace.'},

    # ── Inglés ──
    {'id': 'primera_palabra', 'nombre': 'First Word', 'categoria': 'ingles', 'metrica': 'palabras', 'meta': 1,
     'icono': 'bi-chat-quote-fill', 'rareza': 'bronce',
     'descripcion': 'Agrega tu primera palabra de vocabulario.',
     'frase': 'Every expert was once a beginner.'},
    {'id': 'coleccionista', 'nombre': 'Coleccionista', 'categoria': 'ingles', 'metrica': 'palabras', 'meta': 50,
     'icono': 'bi-journal-bookmark-fill', 'rareza': 'plata',
     'descripcion': 'Agrega 50 palabras de vocabulario.',
     'frase': 'Cada palabra nueva abre una puerta nueva.'},
    {'id': 'diccionario_viviente', 'nombre': 'Diccionario Viviente', 'categoria': 'ingles', 'metrica': 'palabras', 'meta': 200,
     'icono': 'bi-book-half', 'rareza': 'oro',
     'descripcion': 'Agrega 200 palabras de vocabulario.',
     'frase': 'Your words are your superpower.'},
    {'id': 'memoria_de_acero', 'nombre': 'Memoria de Acero', 'categoria': 'ingles', 'metrica': 'repasos', 'meta': 100,
     'icono': 'bi-lightbulb-fill', 'rareza': 'plata',
     'descripcion': 'Repasa vocabulario 100 veces.',
     'frase': 'Repetir es el secreto de recordar.'},
    {'id': 'eco', 'nombre': 'Eco', 'categoria': 'ingles', 'metrica': 'shadowing_min', 'meta': 10,
     'icono': 'bi-mic-fill', 'rareza': 'bronce',
     'descripcion': 'Practica 10 minutos de shadowing.',
     'frase': 'Tu voz en inglés empieza hoy.'},
    {'id': 'voz_fluida', 'nombre': 'Voz Fluida', 'categoria': 'ingles', 'metrica': 'shadowing_min', 'meta': 300,
     'icono': 'bi-soundwave', 'rareza': 'diamante',
     'descripcion': 'Acumula 5 horas de shadowing.',
     'frase': 'Fluency is built one sentence at a time.'},

    # ── Especiales ──
    {'id': 'palabra_cumplida', 'nombre': 'Palabra Cumplida', 'categoria': 'especial', 'metrica': 'castigos', 'meta': 1,
     'icono': 'bi-hand-thumbs-up-fill', 'rareza': 'plata',
     'descripcion': 'Cumple un castigo de la ruleta.',
     'frase': 'Asumir tus fallos también es ganar.'},
]


for _m in MEDALLAS:
    _m.setdefault('rango', None)
    _m.setdefault('nivel_requerido', 0)


# ── 100 medallas de rango ──
# Cada rango exige llegar a un nivel de "Mi Nivel Personal" además de cumplir
# la meta. Son difíciles a propósito, pero alcanzables con constancia.
RANGOS = [
    {'numero': 1, 'nombre': 'Despertar', 'nivel': 2,  'rareza': 'plata',
     'lema': 'Los primeros pasos de alguien que decidió cambiar.'},
    {'numero': 2, 'nombre': 'Forja',     'nivel': 4,  'rareza': 'oro',
     'lema': 'La disciplina se templa a fuego lento.'},
    {'numero': 3, 'nombre': 'Ascenso',   'nivel': 6,  'rareza': 'oro',
     'lema': 'Ya no subes por suerte: subes por costumbre.'},
    {'numero': 4, 'nombre': 'Élite',     'nivel': 8,  'rareza': 'diamante',
     'lema': 'Muy pocos llegan hasta aquí.'},
    {'numero': 5, 'nombre': 'Leyenda',   'nivel': 10, 'rareza': 'mitica',
     'lema': 'Lo que hiciste durante meses ahora es quien eres.'},
]

# Categoría de cada métrica
_CATEGORIA_METRICA = {
    'completados': 'habitos', 'creados': 'habitos', 'dias_perfectos': 'habitos', 'meses_80': 'habitos',
    'racha_max': 'racha', 'dias_activos': 'racha',
    'xp': 'nivel',
    'tareas': 'tareas',
    'palabras': 'ingles', 'repasos': 'ingles', 'vocab_dominadas': 'ingles',
    'shadowing_min': 'ingles', 'shadowing_sesiones': 'ingles',
    'metodos': 'estudio', 'tarjetas_hechas': 'estudio', 'apuntes': 'estudio',
    'castigos': 'especial',
}


def _descripcion(metrica, meta):
    if metrica == 'shadowing_min' and meta >= 120:
        return f'Acumula {meta // 60} horas de shadowing.'
    unicas = {
        ('apuntes', 1): 'Sube tu primer apunte a una tarjeta terminada.',
        ('meses_80', 1): 'Termina un mes con un promedio de 80% o más.',
    }
    if (metrica, meta) in unicas:
        return unicas[(metrica, meta)]
    plantillas = {
        'completados': 'Completa {} hábitos.',
        'creados': 'Ten {} hábitos distintos creados.',
        'dias_perfectos': 'Completa todos los hábitos que te tocaban en un día, {} veces.',
        'meses_80': 'Termina {} meses con un promedio de 80% o más.',
        'racha_max': 'Logra una racha de {} días seguidos.',
        'dias_activos': 'Acumula {} días con al menos un hábito completado.',
        'xp': 'Acumula {} XP.',
        'tareas': 'Completa {} tareas del día.',
        'palabras': 'Agrega {} palabras de vocabulario.',
        'repasos': 'Repasa vocabulario {} veces.',
        'vocab_dominadas': 'Domina {} palabras (su último repaso fue "fácil").',
        'shadowing_min': 'Acumula {} minutos de shadowing.',
        'shadowing_sesiones': 'Completa {} sesiones de shadowing.',
        'metodos': 'Crea {} métodos de estudio.',
        'tarjetas_hechas': 'Lleva {} tarjetas del Kanban a "Hecho".',
        'apuntes': 'Sube {} apuntes a tus tarjetas terminadas.',
        'castigos': 'Cumple {} castigos de la ruleta.',
    }
    return plantillas[metrica].format(f'{meta:,}'.replace(',', '.'))


# (id, nombre, métrica, meta, ícono, frase) — 20 por rango
_MEDALLAS_POR_RANGO = {
    1: [
        ('r1_ritmo', 'Ritmo Propio', 'completados', 150, 'bi-music-note-beamed', 'Encontraste tu ritmo. No lo sueltes.'),
        ('r1_doscientos', 'Doble Centena', 'completados', 200, 'bi-check2-all', 'Doscientas veces dijiste "sí" a tu mejor versión.'),
        ('r1_diez_seguidos', 'Diez al Hilo', 'racha_max', 10, 'bi-link-45deg', 'Diez eslabones forman una cadena que ya pesa.'),
        ('r1_tres_semanas', 'Tres Semanas', 'racha_max', 21, 'bi-calendar3-week', 'Dicen que 21 días crean un hábito. Lo comprobaste.'),
        ('r1_mes_activo', 'Mes Activo', 'dias_activos', 30, 'bi-calendar-check', 'Treinta días eligiendo avanzar.'),
        ('r1_chispa_xp', 'Chispa de XP', 'xp', 750, 'bi-lightning', 'Cada punto de experiencia es una promesa cumplida.'),
        ('r1_mil_xp', 'Mil Puntos', 'xp', 1000, 'bi-lightning-charge', 'Mil XP: tu esfuerzo ya se puede medir.'),
        ('r1_dia_perfecto', 'Día Perfecto', 'dias_perfectos', 3, 'bi-brightness-high', 'Un día sin pendientes se siente increíble, ¿verdad?'),
        ('r1_semana_perfecta', 'Siete Días Perfectos', 'dias_perfectos', 7, 'bi-sun', 'Siete días completos. Eso no es suerte.'),
        ('r1_cuatro_habitos', 'Rutina Armada', 'creados', 4, 'bi-grid-1x2', 'Una buena rutina tiene varias piezas.'),
        ('r1_cincuenta_tareas', 'Lista Vencida', 'tareas', 50, 'bi-list-check', 'Cincuenta tareas fuera de tu cabeza.'),
        ('r1_kanban_cinco', 'Primeras Victorias', 'tarjetas_hechas', 5, 'bi-kanban', 'Mover una tarjeta a "Hecho" nunca pasa de moda.'),
        ('r1_dos_metodos', 'Dos Caminos', 'metodos', 2, 'bi-signpost-2', 'Quien conoce varios métodos aprende más rápido.'),
        ('r1_primer_apunte', 'Primer Apunte', 'apuntes', 1, 'bi-paperclip', 'Lo que se escribe, se recuerda.'),
        ('r1_veinticinco_palabras', 'Vocabulario en Marcha', 'palabras', 25, 'bi-chat-left-text', 'Twenty-five words closer to fluency.'),
        ('r1_cincuenta_repasos', 'Repaso Constante', 'repasos', 50, 'bi-arrow-repeat', 'Repasar hoy es no olvidar mañana.'),
        ('r1_diez_dominadas', 'Diez Dominadas', 'vocab_dominadas', 10, 'bi-check-circle', 'Ya no las buscas: ya las sabes.'),
        ('r1_media_hora_voz', 'Media Hora de Voz', 'shadowing_min', 30, 'bi-mic', 'Tu acento mejora cada vez que repites.'),
        ('r1_cinco_sesiones', 'Sombra Fiel', 'shadowing_sesiones', 5, 'bi-person-video3', 'Cinco sesiones siguiendo voces nativas.'),
        ('r1_tres_castigos', 'Honor Cumplido', 'castigos', 3, 'bi-hand-thumbs-up', 'Pagar tus deudas contigo mismo también es disciplina.'),
    ],
    2: [
        ('r2_trescientos', 'Trescientos', 'completados', 300, 'bi-shield-check', 'Como los 300 de Esparta: firmes ante todo.'),
        ('r2_cuatrocientos', 'Muralla', 'completados', 400, 'bi-bricks', 'Cada hábito es un ladrillo. Ya tienes una muralla.'),
        ('r2_mes_y_medio', 'Mes y Medio', 'racha_max', 45, 'bi-fire', 'Cuarenta y cinco días sin apagar el fuego.'),
        ('r2_setenta_cinco_dias', 'Presencia', 'dias_activos', 75, 'bi-calendar2-check', 'Estuviste presente 75 días. Se nota.'),
        ('r2_tres_mil_xp', 'Tres Mil', 'xp', 3000, 'bi-lightning-charge-fill', 'Tu barra de experiencia ya no es la de un novato.'),
        ('r2_cuatro_mil_xp', 'Cuatro Mil', 'xp', 4000, 'bi-battery-charging', 'Energía acumulada para lo que viene.'),
        ('r2_quince_perfectos', 'Quincena Impecable', 'dias_perfectos', 15, 'bi-brightness-high-fill', 'Quince días sin dejar nada pendiente.'),
        ('r2_veinticinco_perfectos', 'Pulcritud', 'dias_perfectos', 25, 'bi-stars', 'La excelencia es un hábito, no un acto.'),
        ('r2_seis_habitos', 'Sistema Completo', 'creados', 6, 'bi-grid-3x2-gap', 'Tu vida ya tiene un sistema, no solo intenciones.'),
        ('r2_ciento_cincuenta_tareas', 'Productividad Real', 'tareas', 150, 'bi-clipboard-check', 'Ciento cincuenta tareas: hechos, no planes.'),
        ('r2_veinte_tarjetas', 'Tablero en Movimiento', 'tarjetas_hechas', 20, 'bi-kanban-fill', 'Veinte temas estudiados y terminados.'),
        ('r2_cuatro_metodos', 'Estratega del Estudio', 'metodos', 4, 'bi-diagram-3', 'Cada tema merece el método correcto.'),
        ('r2_diez_apuntes', 'Archivo Personal', 'apuntes', 10, 'bi-folder2-open', 'Tu propia biblioteca empieza a crecer.'),
        ('r2_cien_palabras', 'Cien Palabras', 'palabras', 100, 'bi-journal-text', 'One hundred words, one hundred new doors.'),
        ('r2_doscientos_cincuenta_repasos', 'Memoria Entrenada', 'repasos', 250, 'bi-lightbulb', 'Tu memoria es un músculo y lo estás entrenando.'),
        ('r2_cincuenta_dominadas', 'Medio Centenar Dominado', 'vocab_dominadas', 50, 'bi-patch-check', 'Cincuenta palabras que ya son tuyas.'),
        ('r2_dos_horas_voz', 'Dos Horas de Voz', 'shadowing_min', 120, 'bi-headphones', 'Two hours of listening and speaking. Keep going.'),
        ('r2_quince_sesiones', 'Eco Constante', 'shadowing_sesiones', 15, 'bi-broadcast', 'Quince sesiones afinando tu oído.'),
        ('r2_cinco_castigos', 'Palabra de Hierro', 'castigos', 5, 'bi-shield-fill-check', 'Cumples incluso cuando no te gusta.'),
        ('r2_mes_brillante', 'Mes Brillante', 'meses_80', 1, 'bi-bar-chart-fill', 'Un mes entero por encima del 80%. Increíble.'),
    ],
    3: [
        ('r3_seiscientos', 'Seiscientos', 'completados', 600, 'bi-graph-up-arrow', 'Tu gráfico de progreso solo apunta hacia arriba.'),
        ('r3_setecientos_cincuenta', 'Inercia Positiva', 'completados', 750, 'bi-arrow-up-right-circle', 'Ahora lo difícil sería parar.'),
        ('r3_setenta_cinco_racha', 'Llama Eterna', 'racha_max', 75, 'bi-fire', 'Setenta y cinco días: tu fuego ya no se apaga.'),
        ('r3_ciento_veinte_dias', 'Cuatro Meses', 'dias_activos', 120, 'bi-calendar-range', 'Un tercio del año construyendo hábitos.'),
        ('r3_siete_mil_xp', 'Siete Mil Quinientos', 'xp', 7500, 'bi-rocket', 'Despegaste. No mires atrás.'),
        ('r3_nueve_mil_xp', 'Nueve Mil', 'xp', 9000, 'bi-rocket-fill', '¡Es más de nueve mil! Bueno, casi.'),
        ('r3_cuarenta_perfectos', 'Precisión', 'dias_perfectos', 40, 'bi-bullseye', 'Cuarenta días dando en el blanco.'),
        ('r3_sesenta_perfectos', 'Maestría Diaria', 'dias_perfectos', 60, 'bi-sunrise', 'Dos meses de días perfectos.'),
        ('r3_ocho_habitos', 'Arquitecto Mayor', 'creados', 8, 'bi-building', 'Construiste una vida con estructura.'),
        ('r3_doscientas_cincuenta_tareas', 'Imparable en la Lista', 'tareas', 250, 'bi-card-checklist', 'Doscientas cincuenta tareas tachadas.'),
        ('r3_cuarenta_tarjetas', 'Estudiante Incansable', 'tarjetas_hechas', 40, 'bi-mortarboard', 'Cuarenta temas completados en tu tablero.'),
        ('r3_seis_metodos', 'Caja de Herramientas', 'metodos', 6, 'bi-tools', 'Tienes una herramienta para cada desafío.'),
        ('r3_veinticinco_apuntes', 'Biblioteca Viva', 'apuntes', 25, 'bi-archive', 'Veinticinco apuntes listos para repasar.'),
        ('r3_trescientas_palabras', 'Trescientas Palabras', 'palabras', 300, 'bi-book', 'You can already hold real conversations.'),
        ('r3_quinientos_repasos', 'Quinientos Repasos', 'repasos', 500, 'bi-arrow-clockwise', 'La repetición convierte lo difícil en natural.'),
        ('r3_ciento_veinte_dominadas', 'Dominio del Idioma', 'vocab_dominadas', 120, 'bi-translate', 'Ciento veinte palabras sin dudar.'),
        ('r3_diez_horas_voz', 'Diez Horas de Voz', 'shadowing_min', 600, 'bi-soundwave', 'Ten hours of shadowing. Your ear has changed.'),
        ('r3_treinta_sesiones', 'Voz Gemela', 'shadowing_sesiones', 30, 'bi-people', 'Treinta sesiones hablando como un nativo.'),
        ('r3_diez_castigos', 'Responsable', 'castigos', 10, 'bi-award', 'Diez veces asumiste las consecuencias.'),
        ('r3_dos_meses_brillantes', 'Doble Brillo', 'meses_80', 2, 'bi-bar-chart-line-fill', 'Dos meses por encima del 80%. No fue casualidad.'),
    ],
    4: [
        ('r4_mil', 'Mil Victorias', 'completados', 1000, 'bi-trophy', 'Mil hábitos completados. Eres de otra liga.'),
        ('r4_mil_doscientos_cincuenta', 'Titán', 'completados', 1250, 'bi-shield-shaded', 'Tu constancia ya parece la de un titán.'),
        ('r4_ciento_veinte_racha', 'Cuatro Meses Seguidos', 'racha_max', 120, 'bi-fire', 'Ciento veinte días sin fallar. Leyenda en camino.'),
        ('r4_medio_anio', 'Medio Año', 'dias_activos', 180, 'bi-hourglass-split', 'Medio año eligiéndote cada día.'),
        ('r4_catorce_mil_xp', 'Catorce Mil', 'xp', 14000, 'bi-gem', 'Tu experiencia ya vale oro… y diamante.'),
        ('r4_dieciseis_mil_xp', 'Dieciséis Mil', 'xp', 16000, 'bi-diamond-fill', 'Cada XP cuenta la historia de un esfuerzo.'),
        ('r4_noventa_perfectos', 'Trimestre Perfecto', 'dias_perfectos', 90, 'bi-sun-fill', 'Noventa días impecables.'),
        ('r4_ciento_veinte_perfectos', 'Impecable', 'dias_perfectos', 120, 'bi-stars', 'Ciento veinte días sin dejar nada atrás.'),
        ('r4_nueve_habitos', 'Ingeniero de Vida', 'creados', 9, 'bi-gear-wide-connected', 'Nueve hábitos funcionando como un reloj.'),
        ('r4_cuatrocientas_tareas', 'Ejecutor de Élite', 'tareas', 400, 'bi-check2-square', 'Cuatrocientas tareas: tu lista te teme.'),
        ('r4_setenta_cinco_tarjetas', 'Sabio en Formación', 'tarjetas_hechas', 75, 'bi-mortarboard-fill', 'Setenta y cinco temas dominados.'),
        ('r4_ocho_metodos', 'Maestro de Métodos', 'metodos', 8, 'bi-easel', 'Sabes cómo aprender cualquier cosa.'),
        ('r4_cincuenta_apuntes', 'Enciclopedia', 'apuntes', 50, 'bi-journals', 'Cincuenta apuntes: tu propia enciclopedia.'),
        ('r4_quinientas_palabras', 'Quinientas Palabras', 'palabras', 500, 'bi-book-half', 'Five hundred words. You think in English now.'),
        ('r4_mil_repasos', 'Mil Repasos', 'repasos', 1000, 'bi-infinity', 'Mil repasos: tu memoria es de acero.'),
        ('r4_doscientas_cincuenta_dominadas', 'Políglota en Camino', 'vocab_dominadas', 250, 'bi-globe2', 'Doscientas cincuenta palabras dominadas.'),
        ('r4_veinte_horas_voz', 'Veinte Horas de Voz', 'shadowing_min', 1200, 'bi-mic-fill', 'Twenty hours. You sound more natural every day.'),
        ('r4_sesenta_sesiones', 'Sombra Maestra', 'shadowing_sesiones', 60, 'bi-person-video2', 'Sesenta sesiones de práctica de voz.'),
        ('r4_quince_castigos', 'Integridad', 'castigos', 15, 'bi-shield-lock', 'Tu palabra vale, incluso contigo mismo.'),
        ('r4_cuatro_meses_brillantes', 'Temporada Brillante', 'meses_80', 4, 'bi-graph-up', 'Cuatro meses brillando por encima del 80%.'),
    ],
    5: [
        ('r5_mil_quinientos', 'Mil Quinientos', 'completados', 1500, 'bi-trophy-fill', 'Mil quinientas veces cumpliste. Eres leyenda.'),
        ('r5_dos_mil', 'Dos Mil', 'completados', 2000, 'bi-stars', 'Dos mil hábitos. Ya no hay vuelta atrás.'),
        ('r5_medio_anio_racha', 'Medio Año Seguido', 'racha_max', 180, 'bi-fire', 'Ciento ochenta días sin romper la cadena.'),
        ('r5_anio_racha', 'Un Año Invicto', 'racha_max', 365, 'bi-calendar-heart-fill', 'Un año entero sin fallar un solo día. Histórico.'),
        ('r5_trescientos_dias', 'Trescientos Días', 'dias_activos', 300, 'bi-calendar-event', 'Trescientos días construyendo tu leyenda.'),
        ('r5_anio_activo', 'Año de Hierro', 'dias_activos', 365, 'bi-calendar2-heart', 'Un año de días activos. Te transformaste.'),
        ('r5_veintidos_mil_xp', 'Cima de XP', 'xp', 22500, 'bi-award-fill', 'Llegaste a la XP del nivel máximo.'),
        ('r5_treinta_mil_xp', 'Más Allá del Límite', 'xp', 30000, 'bi-rocket-takeoff-fill', 'Superaste el máximo. Plus Ultra.'),
        ('r5_ciento_ochenta_perfectos', 'Perfección', 'dias_perfectos', 180, 'bi-gem', 'Medio año de días perfectos. Sin palabras.'),
        ('r5_doce_habitos', 'Gran Arquitecto', 'creados', 12, 'bi-bank', 'Doce hábitos sostienen tu vida como columnas.'),
        ('r5_seiscientas_tareas', 'Señor de las Tareas', 'tareas', 600, 'bi-clipboard2-check-fill', 'Seiscientas tareas cumplidas.'),
        ('r5_ciento_veinte_tarjetas', 'Erudito', 'tarjetas_hechas', 120, 'bi-bookmark-star-fill', 'Ciento veinte temas estudiados de principio a fin.'),
        ('r5_cien_apuntes', 'Gran Biblioteca', 'apuntes', 100, 'bi-collection-fill', 'Cien apuntes: un legado de conocimiento.'),
        ('r5_mil_palabras', 'Mil Palabras', 'palabras', 1000, 'bi-chat-quote-fill', 'A thousand words. The language is yours.'),
        ('r5_dos_mil_repasos', 'Memoria Legendaria', 'repasos', 2000, 'bi-infinity', 'Dos mil repasos. Nada se te escapa.'),
        ('r5_quinientas_dominadas', 'Bilingüe', 'vocab_dominadas', 500, 'bi-translate', 'Quinientas palabras dominadas. Eres bilingüe.'),
        ('r5_cincuenta_horas_voz', 'Cincuenta Horas de Voz', 'shadowing_min', 3000, 'bi-soundwave', 'Fifty hours. You speak with confidence.'),
        ('r5_cien_sesiones', 'Voz de Leyenda', 'shadowing_sesiones', 100, 'bi-megaphone-fill', 'Cien sesiones: tu voz ya no tiembla.'),
        ('r5_veinticinco_castigos', 'Código de Honor', 'castigos', 25, 'bi-shield-fill', 'Veinticinco castigos cumplidos. Honor intacto.'),
        ('r5_seis_meses_brillantes', 'Medio Año Brillante', 'meses_80', 6, 'bi-lightbulb-fill', 'Seis meses por encima del 80%. Leyenda absoluta.'),
    ],
}

for _rango in RANGOS:
    for _id, _nombre, _metrica, _meta, _icono, _frase in _MEDALLAS_POR_RANGO[_rango['numero']]:
        MEDALLAS.append({
            'id': _id, 'nombre': _nombre, 'categoria': _CATEGORIA_METRICA[_metrica],
            'metrica': _metrica, 'meta': _meta, 'icono': _icono,
            'rareza': _rango['rareza'], 'descripcion': _descripcion(_metrica, _meta), 'frase': _frase,
            'rango': _rango['numero'], 'nivel_requerido': _rango['nivel'],
        })


def _dias_perfectos(idUser):
    """Días en que se completaron todos los hábitos activos que tocaban ese día."""
    habitos = Habit.query.filter_by(idUser=idUser, habitState='Activo').all()
    hechos = {}
    for r in HistHabit.query.filter_by(idUser=idUser).all():
        hechos.setdefault(r.fecha, set()).add(r.idHabit)
    perfectos = 0
    for fecha, ids in hechos.items():
        tocaban = {h.idHabit for h in habitos
                   if h.createdAt.date() <= fecha and fecha.weekday() in h.dias_lista()}
        if tocaban and tocaban <= ids:
            perfectos += 1
    return perfectos


def _meses_80(idUser):
    """Meses ya terminados con un promedio de cumplimiento de 80% o más."""
    hoy = date.today()
    total = 0
    for m in meses_disponibles(idUser, hoy)[1:]:  # el primero es el mes en curso
        anio, mes = (int(p) for p in m['valor'].split('-'))
        promedio = estadisticas_del_mes(idUser, anio, mes, hoy)['promedio']
        if promedio is not None and promedio >= 80:
            total += 1
    return total


def _vocab_dominadas(idUser):
    """Palabras cuyo último repaso se calificó como 'fácil'."""
    ultima = {}
    for r in VocabularioRegistro.query.filter_by(idUser=idUser).order_by(VocabularioRegistro.fecha.desc()).all():
        ultima.setdefault(r.idVocab or r.palabraNombre, r.calificacion)
    return sum(1 for c in ultima.values() if c == 'facil')


def obtener_metricas(idUser):
    """Reúne en un dict todos los contadores que usan las medallas."""
    progress = get_or_create_progress(idUser)
    _, racha_maxima = sincronizar_racha(progress)
    db.session.commit()

    creados = Habit.query.filter_by(idUser=idUser).count()
    segundos_shadowing = db.session.query(
        func.coalesce(func.sum(ShadowingSesion.duracionSegundos), 0)
    ).filter(ShadowingSesion.idUser == idUser).scalar()

    return {
        'completados': HistHabit.query.filter_by(idUser=idUser).count(),
        'creados': creados,
        'racha_max': max(progress.rachaMaxima, racha_maxima),
        'dias_activos': db.session.query(func.count(func.distinct(HistHabit.fecha)))
                          .filter(HistHabit.idUser == idUser).scalar(),
        'nivel': calcular_progreso(progress.xpTotal, creados)['nivel'],
        'tareas': Tarea.query.filter_by(idUser=idUser, completada=True).count(),
        'palabras': Vocabulario.query.filter_by(idUser=idUser).count(),
        'repasos': VocabularioRegistro.query.filter_by(idUser=idUser).count(),
        'shadowing_min': int(segundos_shadowing) // 60,
        'castigos': Castigo.query.filter_by(idUser=idUser, castigoState='Completado').count(),
        'xp': progress.xpTotal,
        'dias_perfectos': _dias_perfectos(idUser),
        'meses_80': _meses_80(idUser),
        'vocab_dominadas': _vocab_dominadas(idUser),
        'shadowing_sesiones': ShadowingSesion.query.filter_by(idUser=idUser).count(),
        'metodos': MetodoEstudio.query.filter_by(idUser=idUser).count(),
        'tarjetas_hechas': KanbanTarjeta.query.filter_by(idUser=idUser, columna='hecho').count(),
        'apuntes': Apunte.query.filter_by(idUser=idUser).count(),
    }


def evaluar_medallas(metricas):
    """Devuelve la lista de medallas con su progreso y si están desbloqueadas."""
    resultado = []
    nivel = metricas.get('nivel', 1)
    for m in MEDALLAS:
        actual = metricas.get(m['metrica'], 0)
        falta_nivel = nivel < m['nivel_requerido']
        resultado.append({
            **m,
            'actual': min(actual, m['meta']),
            'falta_nivel': falta_nivel,
            'desbloqueada': actual >= m['meta'] and not falta_nivel,
            'pct': min(100, round(actual / m['meta'] * 100)),
        })
    return resultado
