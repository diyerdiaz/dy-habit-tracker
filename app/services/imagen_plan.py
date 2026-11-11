"""Imagen (PNG) del plan de hábitos de un mes: qué hábitos tocan cada día de la
semana. Se manda por correo al empezar el mes para tenerla sin internet.

Lleva el personaje del correo y los colores de su tema, así cada mes puede salir
de un color distinto (violeta, cian, dorado, rojo o verde).

Se dibuja con Pillow usando DejaVu Sans (el Dockerfile instala fonts-dejavu-core).
Si no estuviera instalada, usa la fuente de Pillow y quita las tildes, que esa
fuente no tiene: la imagen sale igual, sin cuadros rotos."""

import os
import unicodedata
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from app.models.habitos import DIAS_SEMANA
from app.models.plan_mensual import MESES
from app.services.personajes_login import PERSONAJES

DIAS_COMPLETOS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

TEXTO = (255, 255, 255)
TEXTO_SUAVE = (200, 195, 210)
FILA_PAR = (255, 255, 255, 14)
LINEA = (255, 255, 255, 40)

ANCHO = 1080          # se ve bien en el celular
MARGEN = 48
ANCHO_NOMBRE = 400    # columna con el nombre del hábito
ALTO_FILA = 76
ALTO_CABECERA = 270
ALTO_PERSONAJE = 240

# Dónde queda DejaVu Sans en Debian (servidor) y en Arch/Manjaro
CARPETAS_FUENTE = ['/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/TTF', '/usr/share/fonts/dejavu']


def plan_por_dia(habitos):
    """[(día, [hábitos de ese día]), ...] de lunes a domingo.
    `habitos`: lista de (nombre, [índices de días 0-6])."""
    return [(DIAS_COMPLETOS[d], [nombre for nombre, dias in habitos if d in dias]) for d in range(7)]


@lru_cache(maxsize=None)
def _archivo_fuente(negrita):
    nombre = 'DejaVuSans-Bold.ttf' if negrita else 'DejaVuSans.ttf'
    for carpeta in CARPETAS_FUENTE:
        ruta = os.path.join(carpeta, nombre)
        if os.path.exists(ruta):
            return ruta
    return None


def hay_fuente_con_tildes():
    return _archivo_fuente(False) is not None


def _fuente(tamano, negrita=False):
    ruta = _archivo_fuente(negrita)
    return ImageFont.truetype(ruta, tamano) if ruta else ImageFont.load_default(size=tamano)


def _texto(texto):
    """Sin DejaVu, la fuente de Pillow no tiene tildes: "hábito" -> "habito"."""
    if hay_fuente_con_tildes():
        return texto
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')


def _rgb(hexadecimal):
    hexadecimal = hexadecimal.lstrip('#')
    return tuple(int(hexadecimal[i:i + 2], 16) for i in (0, 2, 4))


def colores_del_tema(tema):
    """Colores de la imagen a partir del tema de un personaje."""
    vivo = _rgb(tema['vivo'])
    luminancia = 0.2126 * vivo[0] + 0.7152 * vivo[1] + 0.0722 * vivo[2]
    return {
        'vivo': vivo,
        'cabecera': _rgb(tema['grad-1']),
        'fondo_arriba': _rgb(tema['oscuro']),
        'fondo_abajo': tuple(c // 3 for c in _rgb(tema['oscuro-2'])),
        # Palomita oscura sobre colores claros (dorado, cian, verde); blanca sobre los demás
        'palomita': _rgb(tema['oscuro-2']) if luminancia > 150 else TEXTO,
    }


def _recortar(dibujo, texto, fuente, ancho_max):
    """Corta el texto con "…" si no cabe en `ancho_max` píxeles."""
    if dibujo.textlength(texto, font=fuente) <= ancho_max:
        return texto
    while texto and dibujo.textlength(texto + '…', font=fuente) > ancho_max:
        texto = texto[:-1]
    return texto.rstrip() + '…'


def _check(dibujo, cx, cy, radio, colores):
    """Círculo de color con una palomita: ese día toca el hábito."""
    dibujo.ellipse((cx - radio, cy - radio, cx + radio, cy + radio), fill=colores['vivo'])
    puntos = [(cx - radio * 0.45, cy + radio * 0.02), (cx - radio * 0.1, cy + radio * 0.38),
              (cx + radio * 0.5, cy - radio * 0.35)]
    dibujo.line(puntos, fill=colores['palomita'], width=max(3, radio // 5), joint='curve')


def _personaje_sin_fondo(jpg, color_fondo):
    """El JPG del personaje tiene de fondo el color oscuro de su tema: ese fondo
    se vuelve transparente para que el personaje se funda con la imagen."""
    personaje = Image.open(BytesIO(jpg)).convert('RGB')
    escala = ALTO_PERSONAJE / personaje.height
    personaje = personaje.resize((round(personaje.width * escala), ALTO_PERSONAJE), Image.LANCZOS)
    diferencia = ImageChops.difference(personaje, Image.new('RGB', personaje.size, color_fondo)).convert('L')
    mascara = diferencia.point(lambda v: 255 if v > 22 else 0).filter(ImageFilter.GaussianBlur(1.2))
    personaje.putalpha(mascara)
    return personaje


def imagen_plan_png(nombre_usuario, habitos, anio, mes, personaje=0, personaje_jpg=None):
    """PNG con la tabla semanal del plan. `habitos`: lista de (nombre, [días 0-6]).
    `personaje`: índice del personaje (define los colores); `personaje_jpg`: su
    imagen para ponerla arriba a la derecha (sin ella, solo se usan sus colores)."""
    tema = PERSONAJES[personaje % len(PERSONAJES)]['tema']
    colores = colores_del_tema(tema)
    columnas = 7
    ancho_dia = (ANCHO - 2 * MARGEN - ANCHO_NOMBRE) // columnas
    alto_tabla = ALTO_FILA * (len(habitos) + 2)  # fila de días + hábitos + totales
    alto = ALTO_CABECERA + alto_tabla + 110

    imagen = Image.new('RGB', (ANCHO, alto), colores['fondo_abajo'])
    # Degradado vertical: arriba el color oscuro del tema (el del fondo del personaje)
    fondo = ImageDraw.Draw(imagen)
    for y in range(alto):
        t = max(0.0, (y - ALTO_CABECERA * 0.6) / (alto - ALTO_CABECERA * 0.6))
        color = tuple(round(a + (b - a) * t) for a, b in zip(colores['fondo_arriba'], colores['fondo_abajo']))
        fondo.line([(0, y), (ANCHO, y)], fill=color)

    capa = Image.new('RGBA', imagen.size, (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(capa)

    if personaje_jpg:
        figura = _personaje_sin_fondo(personaje_jpg, colores['fondo_arriba'])
        capa.alpha_composite(figura, (ANCHO - MARGEN - figura.width + 10, 14))

    # Encabezado
    dibujo.text((MARGEN, 60), 'DY HABIT TRACKER', font=_fuente(22, True), fill=colores['vivo'])
    dibujo.text((MARGEN, 94), _texto(f'Plan de {MESES[mes - 1]}'), font=_fuente(54, True), fill=TEXTO)
    dibujo.text((MARGEN, 158), str(anio), font=_fuente(40, True), fill=colores['vivo'])
    dibujo.text((MARGEN, 214), _texto(f'{nombre_usuario} · qué hábito toca cada día'),
                font=_fuente(26), fill=TEXTO_SUAVE)

    x_dias = MARGEN + ANCHO_NOMBRE
    y = ALTO_CABECERA
    # Fila con los días
    dibujo.rounded_rectangle((MARGEN, y, ANCHO - MARGEN, y + ALTO_FILA), radius=16,
                             fill=colores['cabecera'] + (150,))
    dibujo.text((MARGEN + 20, y + ALTO_FILA / 2), _texto('Hábito'), font=_fuente(26, True), fill=TEXTO,
                anchor='lm')
    for d, dia in enumerate(DIAS_SEMANA):
        dibujo.text((x_dias + ancho_dia * d + ancho_dia / 2, y + ALTO_FILA / 2), _texto(dia),
                    font=_fuente(26, True), fill=TEXTO, anchor='mm')
    y += ALTO_FILA

    fuente_nombre = _fuente(26)
    for i, (nombre, dias) in enumerate(habitos):
        if i % 2 == 0:
            dibujo.rectangle((MARGEN, y, ANCHO - MARGEN, y + ALTO_FILA), fill=FILA_PAR)
        texto = _recortar(dibujo, _texto(nombre), fuente_nombre, ANCHO_NOMBRE - 36)
        dibujo.text((MARGEN + 20, y + ALTO_FILA / 2), texto, font=fuente_nombre, fill=TEXTO, anchor='lm')
        for d in range(columnas):
            cx = x_dias + ancho_dia * d + ancho_dia // 2
            cy = y + ALTO_FILA // 2
            if d in dias:
                _check(dibujo, cx, cy, 20, colores)
            else:
                dibujo.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=LINEA)
        dibujo.line((MARGEN, y + ALTO_FILA, ANCHO - MARGEN, y + ALTO_FILA), fill=LINEA, width=1)
        y += ALTO_FILA

    # Cuántos hábitos tocan cada día
    dibujo.text((MARGEN + 20, y + ALTO_FILA / 2), _texto('Hábitos del día'), font=_fuente(24),
                fill=TEXTO_SUAVE, anchor='lm')
    for d, (_, del_dia) in enumerate(plan_por_dia(habitos)):
        dibujo.text((x_dias + ancho_dia * d + ancho_dia / 2, y + ALTO_FILA / 2), str(len(del_dia)),
                    font=_fuente(30, True), fill=colores['vivo'], anchor='mm')
    y += ALTO_FILA

    dibujo.text((ANCHO / 2, y + 50), _texto('Guárdala en tu celular para verla sin internet'),
                font=_fuente(24), fill=TEXTO_SUAVE, anchor='mm')

    imagen = Image.alpha_composite(imagen.convert('RGBA'), capa).convert('RGB')
    salida = BytesIO()
    imagen.save(salida, format='PNG', optimize=True)
    return salida.getvalue()
