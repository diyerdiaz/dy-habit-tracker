"""Secciones de idioma: Inglés y Español comparten las mismas páginas de vocabulario
y juegos (el mismo blueprint se registra dos veces, ver app/__init__.py). Aquí está
lo único que cambia entre una y otra: textos, colores, voz y a dónde apuntan los enlaces.
Cada idioma guarda sus propias palabras, repasos y partidas (columna `idioma`)."""
from flask import request

INGLES = 'en'
ESPANOL = 'es'

SECCIONES = {
    INGLES: {
        'idioma': INGLES,
        'nombre': 'Inglés',
        'en_idioma': 'en inglés',
        'banderas': ('🇬🇧', '🇺🇸'),
        'inicio': 'ingles.ingles',
        'inicio_nombre': 'Aprende Inglés',
        'bp_vocab': 'vocabulario',
        'bp_juegos': 'juegos',
        'sidebar': 'ingles/_sidebar_ingles.html',
        'css_extra': None,              # ingles.css ya trae los colores azules
        'voz': 'en-US',                 # voz que lee las palabras en los juegos
        'lang': 'en',
        'marquesina': 'Vocabulario • Gramática • Pronunciación • Conversación • Aprende Inglés •',
        'columna_palabra': 'English',
        'columna_significado': 'Español',
        'autocompletar': True,          # MyMemory + Tatoeba solo traducen desde inglés
        'shadowing': True,              # el dashboard muestra minutos de shadowing
        'titulo_dashboard': 'Tu Inglés', 'badge_dashboard': 'English Dashboard', 'badge_practica': 'Practice Time',
        'ejemplo_nombre': 'Apple', 'ejemplo_significado': 'Manzana',
        'ejemplo_frase': 'I eat an apple every day.',
        'palabras_fondo': ['Hello', 'ABC', 'Learn', 'Yes', 'Go', 'Book', 'Fast', 'Easy', 'Words', 'English'],
    },
    ESPANOL: {
        'idioma': ESPANOL,
        'nombre': 'Español',
        'en_idioma': 'en español',
        'banderas': ('🇪🇸', '🇨🇴'),
        'inicio': 'espanol.index',
        'inicio_nombre': 'Aprende Español',
        'bp_vocab': 'vocabulario_es',
        'bp_juegos': 'juegos_es',
        'sidebar': 'espanol/_sidebar_espanol.html',
        'css_extra': 'css/espanol.css',  # se carga después de ingles.css: pinta todo de rojo y dorado
        'voz': 'es-ES',
        'lang': 'es',
        'marquesina': 'Vocabulario • Ortografía • Significados • Sinónimos • Aprende Español •',
        'columna_palabra': 'Palabra',
        'columna_significado': 'Significado',
        'autocompletar': False,
        'shadowing': False,             # Español es solo para practicar palabras
        'titulo_dashboard': 'Tu Español', 'badge_dashboard': 'Dashboard de Español', 'badge_practica': 'Hora de practicar',
        'ejemplo_nombre': 'Efímero', 'ejemplo_significado': 'Que dura poco tiempo',
        'ejemplo_frase': 'La alegría del momento fue efímera.',
        'palabras_fondo': ['Hola', 'Libro', 'Palabra', 'Sí', 'Leer', 'Casa', 'Ñandú', 'Fácil', 'Idioma', 'Español'],
    },
}

# Nombre con el que se registró cada blueprint -> idioma de sus páginas
_IDIOMA_DE_BLUEPRINT = {
    'ingles': INGLES, 'vocabulario': INGLES, 'juegos': INGLES,
    'espanol': ESPANOL, 'vocabulario_es': ESPANOL, 'juegos_es': ESPANOL,
}


def idioma_actual():
    """Idioma de la página que se está viendo (Inglés si no es de ninguna sección)."""
    return _IDIOMA_DE_BLUEPRINT.get(request.blueprint or '', INGLES)


def seccion_actual():
    return SECCIONES[idioma_actual()]
