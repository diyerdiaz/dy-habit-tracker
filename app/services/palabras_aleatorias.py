"""Palabras aleatorias en inglés para practicar haciendo frases (lista local, sin APIs)."""
import random

MINIMO_PALABRAS = 1
MAXIMO_PALABRAS = 50
CANTIDAD_POR_DEFECTO = 5

# Palabras comunes en inglés con su significado en español
PALABRAS_INGLES = [
    ('house', 'casa'), ('water', 'agua'), ('friend', 'amigo'), ('family', 'familia'),
    ('school', 'escuela'), ('book', 'libro'), ('city', 'ciudad'), ('country', 'país'),
    ('money', 'dinero'), ('time', 'tiempo'), ('day', 'día'), ('night', 'noche'),
    ('morning', 'mañana'), ('week', 'semana'), ('year', 'año'), ('work', 'trabajo'),
    ('car', 'carro'), ('street', 'calle'), ('door', 'puerta'), ('window', 'ventana'),
    ('table', 'mesa'), ('chair', 'silla'), ('bed', 'cama'), ('kitchen', 'cocina'),
    ('food', 'comida'), ('bread', 'pan'), ('coffee', 'café'), ('apple', 'manzana'),
    ('dog', 'perro'), ('cat', 'gato'), ('bird', 'pájaro'), ('tree', 'árbol'),
    ('flower', 'flor'), ('river', 'río'), ('mountain', 'montaña'), ('beach', 'playa'),
    ('sky', 'cielo'), ('sun', 'sol'), ('moon', 'luna'), ('rain', 'lluvia'),
    ('weather', 'clima'), ('music', 'música'), ('song', 'canción'), ('movie', 'película'),
    ('game', 'juego'), ('phone', 'teléfono'), ('computer', 'computadora'), ('job', 'empleo'),
    ('teacher', 'profesor'), ('student', 'estudiante'), ('doctor', 'médico'), ('child', 'niño'),
    ('people', 'gente'), ('world', 'mundo'), ('life', 'vida'), ('heart', 'corazón'),
    ('hand', 'mano'), ('eye', 'ojo'), ('head', 'cabeza'), ('voice', 'voz'),
    ('idea', 'idea'), ('question', 'pregunta'), ('answer', 'respuesta'), ('problem', 'problema'),
    ('story', 'historia'), ('dream', 'sueño'), ('goal', 'meta'), ('habit', 'hábito'),
    ('health', 'salud'), ('trip', 'viaje'), ('gift', 'regalo'), ('party', 'fiesta'),
    ('store', 'tienda'), ('price', 'precio'), ('market', 'mercado'), ('office', 'oficina'),
    ('meeting', 'reunión'), ('letter', 'carta'), ('key', 'llave'), ('bag', 'bolsa'),
    ('clothes', 'ropa'), ('shoes', 'zapatos'), ('hospital', 'hospital'), ('airport', 'aeropuerto'),
    ('train', 'tren'), ('bridge', 'puente'), ('garden', 'jardín'), ('island', 'isla'),
    ('go', 'ir'), ('come', 'venir'), ('eat', 'comer'), ('drink', 'beber'),
    ('sleep', 'dormir'), ('wake up', 'despertar'), ('walk', 'caminar'), ('run', 'correr'),
    ('read', 'leer'), ('write', 'escribir'), ('speak', 'hablar'), ('listen', 'escuchar'),
    ('learn', 'aprender'), ('teach', 'enseñar'), ('buy', 'comprar'), ('sell', 'vender'),
    ('pay', 'pagar'), ('open', 'abrir'), ('close', 'cerrar'), ('give', 'dar'),
    ('take', 'tomar'), ('bring', 'traer'), ('find', 'encontrar'), ('lose', 'perder'),
    ('win', 'ganar'), ('play', 'jugar'), ('sing', 'cantar'), ('dance', 'bailar'),
    ('cook', 'cocinar'), ('clean', 'limpiar'), ('wash', 'lavar'), ('drive', 'manejar'),
    ('travel', 'viajar'), ('build', 'construir'), ('break', 'romper'), ('fix', 'arreglar'),
    ('start', 'empezar'), ('finish', 'terminar'), ('try', 'intentar'), ('help', 'ayudar'),
    ('need', 'necesitar'), ('want', 'querer'), ('love', 'amar'), ('hate', 'odiar'),
    ('think', 'pensar'), ('believe', 'creer'), ('remember', 'recordar'), ('forget', 'olvidar'),
    ('know', 'saber'), ('understand', 'entender'), ('feel', 'sentir'), ('see', 'ver'),
    ('look', 'mirar'), ('watch', 'observar'), ('wait', 'esperar'), ('hope', 'esperar (tener esperanza)'),
    ('change', 'cambiar'), ('choose', 'elegir'), ('decide', 'decidir'), ('explain', 'explicar'),
    ('ask', 'preguntar'), ('tell', 'contar'), ('send', 'enviar'), ('call', 'llamar'),
    ('meet', 'conocer'), ('visit', 'visitar'), ('stay', 'quedarse'), ('leave', 'irse'),
    ('arrive', 'llegar'), ('return', 'regresar'), ('grow', 'crecer'), ('improve', 'mejorar'),
    ('practice', 'practicar'), ('share', 'compartir'), ('save', 'ahorrar'), ('spend', 'gastar'),
    ('borrow', 'pedir prestado'), ('lend', 'prestar'), ('smile', 'sonreír'), ('laugh', 'reír'),
    ('cry', 'llorar'), ('worry', 'preocuparse'), ('enjoy', 'disfrutar'), ('climb', 'escalar'),
    ('big', 'grande'), ('small', 'pequeño'), ('new', 'nuevo'), ('old', 'viejo'),
    ('young', 'joven'), ('good', 'bueno'), ('bad', 'malo'), ('happy', 'feliz'),
    ('sad', 'triste'), ('angry', 'enojado'), ('tired', 'cansado'), ('hungry', 'hambriento'),
    ('busy', 'ocupado'), ('easy', 'fácil'), ('difficult', 'difícil'), ('fast', 'rápido'),
    ('slow', 'lento'), ('hot', 'caliente'), ('cold', 'frío'), ('beautiful', 'hermoso'),
    ('ugly', 'feo'), ('rich', 'rico'), ('poor', 'pobre'), ('strong', 'fuerte'),
    ('weak', 'débil'), ('neat', 'ordenado'), ('dirty', 'sucio'), ('early', 'temprano'),
    ('late', 'tarde'), ('quiet', 'callado'), ('loud', 'ruidoso'), ('important', 'importante'),
    ('dangerous', 'peligroso'), ('expensive', 'caro'), ('cheap', 'barato'), ('brave', 'valiente'),
    ('funny', 'gracioso'), ('kind', 'amable'), ('smart', 'inteligente'), ('lazy', 'perezoso'),
    ('always', 'siempre'), ('never', 'nunca'), ('sometimes', 'a veces'), ('often', 'a menudo'),
    ('today', 'hoy'), ('tomorrow', 'mañana'), ('yesterday', 'ayer'), ('already', 'ya'),
    ('still', 'todavía'), ('together', 'juntos'), ('maybe', 'quizás'), ('because', 'porque'),
    ('although', 'aunque'), ('before', 'antes'), ('after', 'después'), ('during', 'durante'),
]


def normalizar_cantidad(valor):
    """Convierte lo que escribió el usuario en una cantidad válida (entre el mínimo y el máximo).
    Devuelve None si no es un número."""
    try:
        cantidad = int(valor)
    except (TypeError, ValueError):
        return None
    return max(MINIMO_PALABRAS, min(MAXIMO_PALABRAS, cantidad))


def palabras_aleatorias(cantidad):
    """Elige `cantidad` palabras distintas al azar de la lista."""
    elegidas = random.sample(PALABRAS_INGLES, min(cantidad, len(PALABRAS_INGLES)))
    return [{'palabra': palabra, 'significado': significado} for palabra, significado in elegidas]
