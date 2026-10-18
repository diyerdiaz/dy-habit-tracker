"""Personajes anime del login (ilustraciones propias en app/static/img/personajes/).

No se guardan en la base de datos: en cada visita al login se elige uno al azar,
siempre distinto del que se mostró la vez anterior. Cada uno trae su paleta
(`tema`): el login toma su color y, al iniciar sesión, toda la app se queda con
el color del personaje que se estaba viendo.
"""

import random

PERSONAJES = [
    {'archivo': 'personajes/personaje-1.svg', 'nombre': 'Chica de pelo largo, de perfil', 'aura': 'violeta',
     'tema': {'vivo': '#d966ff', 'vivo-rgb': '217, 102, 255', 'fuerte-rgb': '183, 0, 255', 'claro-rgb': '230, 130, 255', 'fondo-rgb': '80, 0, 120', 'grad-1': '#8a28ff', 'grad-2': '#e100ff',
               'grad-1-rgb': '138, 40, 255', 'grad-2-rgb': '225, 0, 255', 'oscuro': '#250035', 'oscuro-2': '#1a002a', 'oscuro-rgb': '30, 0, 45'}},
    {'archivo': 'personajes/personaje-2.svg', 'nombre': 'Chico de pelo en punta, de espaldas', 'aura': 'cian',
     'tema': {'vivo': '#00e5ff', 'vivo-rgb': '0, 229, 255', 'fuerte-rgb': '0, 170, 220', 'claro-rgb': '130, 240, 255', 'fondo-rgb': '0, 50, 90', 'grad-1': '#0057ff', 'grad-2': '#00c8f0',
               'grad-1-rgb': '0, 87, 255', 'grad-2-rgb': '0, 200, 240', 'oscuro': '#002235', 'oscuro-2': '#001a2a', 'oscuro-rgb': '0, 30, 45'}},
    {'archivo': 'personajes/personaje-3.svg', 'nombre': 'Chica de dos coletas, puño en alto', 'aura': 'dorada',
     'tema': {'vivo': '#ffd700', 'vivo-rgb': '255, 215, 0', 'fuerte-rgb': '255, 150, 0', 'claro-rgb': '255, 230, 130', 'fondo-rgb': '90, 55, 0', 'grad-1': '#e65c00', 'grad-2': '#ffb300',
               'grad-1-rgb': '230, 92, 0', 'grad-2-rgb': '255, 179, 0', 'oscuro': '#2e1d00', 'oscuro-2': '#221500', 'oscuro-rgb': '45, 28, 0'}},
    {'archivo': 'personajes/personaje-4.svg', 'nombre': 'Samurái con la katana en vertical', 'aura': 'roja',
     'tema': {'vivo': '#ff4d6d', 'vivo-rgb': '255, 77, 109', 'fuerte-rgb': '255, 26, 64', 'claro-rgb': '255, 150, 170', 'fondo-rgb': '100, 0, 25', 'grad-1': '#b3001b', 'grad-2': '#ff4d6d',
               'grad-1-rgb': '179, 0, 27', 'grad-2-rgb': '255, 77, 109', 'oscuro': '#33000c', 'oscuro-2': '#260009', 'oscuro-rgb': '45, 0, 12'}},
    {'archivo': 'personajes/personaje-5.svg', 'nombre': 'Chica con capucha de gato, sentada', 'aura': 'verde',
     'tema': {'vivo': '#00e676', 'vivo-rgb': '0, 230, 118', 'fuerte-rgb': '0, 200, 120', 'claro-rgb': '150, 255, 200', 'fondo-rgb': '0, 70, 45', 'grad-1': '#00875a', 'grad-2': '#00d26a',
               'grad-1-rgb': '0, 135, 90', 'grad-2-rgb': '0, 210, 106', 'oscuro': '#00261a', 'oscuro-2': '#001c13', 'oscuro-rgb': '0, 40, 28'}},
]


def elegir_personaje(anterior=None, azar=random):
    """Devuelve el índice de un personaje al azar, distinto de `anterior`."""
    opciones = [i for i in range(len(PERSONAJES)) if i != anterior]
    return azar.choice(opciones)


def tema_del_sitio(indice):
    """Paleta del personaje con el que se inició sesión (None si no hay)."""
    if isinstance(indice, int) and 0 <= indice < len(PERSONAJES):
        return PERSONAJES[indice]['tema']
    return None
