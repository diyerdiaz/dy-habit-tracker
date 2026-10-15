"""Frases motivadoras de anime: una distinta cada día.

No se guardan en la base de datos: la frase del día se elige a partir de la
fecha, así todo el día se ve la misma y al día siguiente cambia sola.
"""

from datetime import date, timedelta

FRASES = [
    {'texto': 'Si no te gusta tu destino, no lo aceptes. Ten el valor de cambiarlo como tú quieras.',
     'personaje': 'Naruto Uzumaki', 'anime': 'Naruto', 'icono': 'bi-wind'},
    {'texto': 'El trabajo duro no sirve de nada para quienes no creen en sí mismos.',
     'personaje': 'Naruto Uzumaki', 'anime': 'Naruto', 'icono': 'bi-wind'},
    {'texto': 'No retiro mis palabras. Ese es mi camino ninja.',
     'personaje': 'Naruto Uzumaki', 'anime': 'Naruto', 'icono': 'bi-wind'},
    {'texto': 'Con trabajo duro, hasta alguien sin talento puede superar a un genio.',
     'personaje': 'Rock Lee', 'anime': 'Naruto', 'icono': 'bi-lightning-charge-fill'},
    {'texto': 'Un ninja es aquel que persevera.',
     'personaje': 'Jiraiya', 'anime': 'Naruto', 'icono': 'bi-book-fill'},
    {'texto': 'Si ganas, vives. Si pierdes, mueres. Si no luchas, no puedes ganar.',
     'personaje': 'Eren Jaeger', 'anime': 'Attack on Titan', 'icono': 'bi-shield-shaded'},
    {'texto': 'Quien no es capaz de sacrificar nada, nunca podrá cambiar nada.',
     'personaje': 'Armin Arlert', 'anime': 'Attack on Titan', 'icono': 'bi-shield-shaded'},
    {'texto': 'Lo único que podemos hacer es creer que no nos arrepentiremos de la decisión que tomamos.',
     'personaje': 'Levi Ackerman', 'anime': 'Attack on Titan', 'icono': 'bi-shield-shaded'},
    {'texto': '¡Ve más allá! ¡Plus Ultra!',
     'personaje': 'All Might', 'anime': 'My Hero Academia', 'icono': 'bi-lightning-fill'},
    {'texto': 'Tú puedes convertirte en un héroe.',
     'personaje': 'All Might', 'anime': 'My Hero Academia', 'icono': 'bi-lightning-fill'},
    {'texto': 'Si no te arriesgas, no puedes crear un futuro.',
     'personaje': 'Monkey D. Luffy', 'anime': 'One Piece', 'icono': 'bi-sun-fill'},
    {'texto': '¡Voy a ser el Rey de los Piratas!',
     'personaje': 'Monkey D. Luffy', 'anime': 'One Piece', 'icono': 'bi-sun-fill'},
    {'texto': 'El poder llega como respuesta a una necesidad, no a un deseo.',
     'personaje': 'Goku', 'anime': 'Dragon Ball Z', 'icono': 'bi-stars'},
    {'texto': 'Cien flexiones, cien abdominales, cien sentadillas y diez kilómetros. Todos los días.',
     'personaje': 'Saitama', 'anime': 'One Punch Man', 'icono': 'bi-heart-pulse-fill'},
    {'texto': 'Enciende tu corazón. Ve más allá de tus límites.',
     'personaje': 'Kyojuro Rengoku', 'anime': 'Demon Slayer', 'icono': 'bi-fire'},
    {'texto': '¡Aguanta, Tanjiro! ¡Tú puedes!',
     'personaje': 'Tanjiro Kamado', 'anime': 'Demon Slayer', 'icono': 'bi-water'},
    {'texto': 'Cree en el tú que cree en ti.',
     'personaje': 'Kamina', 'anime': 'Gurren Lagann', 'icono': 'bi-tornado'},
    {'texto': 'Tu taladro es el que perforará los cielos.',
     'personaje': 'Kamina', 'anime': 'Gurren Lagann', 'icono': 'bi-tornado'},
    {'texto': 'Una lección sin dolor no tiene sentido.',
     'personaje': 'Edward Elric', 'anime': 'Fullmetal Alchemist: Brotherhood', 'icono': 'bi-gear-fill'},
    {'texto': 'Levántate y camina. Sigue avanzando. Tienes dos piernas buenas.',
     'personaje': 'Edward Elric', 'anime': 'Fullmetal Alchemist: Brotherhood', 'icono': 'bi-gear-fill'},
    {'texto': 'El talento es algo que haces florecer; el instinto, algo que pules.',
     'personaje': 'Toru Oikawa', 'anime': 'Haikyuu!!', 'icono': 'bi-dribbble'},
    {'texto': 'No todos los que se esfuerzan triunfan, pero todos los que triunfan se esforzaron.',
     'personaje': 'Genji Kamogawa', 'anime': 'Hajime no Ippo', 'icono': 'bi-trophy-fill'},
    {'texto': 'Quiero saber qué se siente ser fuerte.',
     'personaje': 'Ippo Makunouchi', 'anime': 'Hajime no Ippo', 'icono': 'bi-trophy-fill'},
    {'texto': '¡No rendirme nunca, esa es mi magia!',
     'personaje': 'Asta', 'anime': 'Black Clover', 'icono': 'bi-suit-club-fill'},
    {'texto': 'Si te rindes, el partido ya se terminó.',
     'personaje': 'Mitsuyoshi Anzai', 'anime': 'Slam Dunk', 'icono': 'bi-dribbble'},
    {'texto': 'Aunque no pueda usar ninjutsu ni genjutsu, demostraré que puedo ser un gran ninja.',
     'personaje': 'Rock Lee', 'anime': 'Naruto', 'icono': 'bi-lightning-charge-fill'},
    {'texto': 'Sigue avanzando.',
     'personaje': 'Eren Jaeger', 'anime': 'Attack on Titan', 'icono': 'bi-shield-shaded'},
    {'texto': 'Un verdadero guerrero no necesita espada.',
     'personaje': 'Thors', 'anime': 'Vinland Saga', 'icono': 'bi-compass-fill'},
    {'texto': 'Voy a ser el mejor espadachín del mundo.',
     'personaje': 'Roronoa Zoro', 'anime': 'One Piece', 'icono': 'bi-sun-fill'},
    {'texto': '¡Entreguen sus corazones!',
     'personaje': 'Erwin Smith', 'anime': 'Attack on Titan', 'icono': 'bi-shield-shaded'},
]

# Mensaje corto para aplicar la frase a los hábitos, uno por cada día de la semana
RETOS = [
    'Empieza la semana completando tu hábito más difícil primero.',
    'Hoy no te saltes ningún hábito, aunque sea en su versión más corta.',
    'Mitad de semana: revisa tu racha y no la dejes caer.',
    'Haz hoy un poco más de lo que hiciste ayer.',
    'Cierra la semana fuerte: termina todas tus tareas del día.',
    'Aprovecha el sábado para practicar inglés aunque sea 10 minutos.',
    'Domingo: descansa, pero planea los hábitos de la semana.',
]


def frase_del_dia(fecha=None):
    """Devuelve la frase que corresponde a una fecha (por defecto, hoy)."""
    fecha = fecha or date.today()
    return FRASES[fecha.toordinal() % len(FRASES)]


def reto_del_dia(fecha=None):
    fecha = fecha or date.today()
    return RETOS[fecha.weekday()]


def frases_anteriores(dias=6, fecha=None):
    """Las frases de los días anteriores, de la más reciente a la más antigua."""
    fecha = fecha or date.today()
    return [
        {'fecha': fecha - timedelta(days=i), **frase_del_dia(fecha - timedelta(days=i))}
        for i in range(1, dias + 1)
    ]
