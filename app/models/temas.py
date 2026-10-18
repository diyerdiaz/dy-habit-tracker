"""Temas aleatorios: la persona guarda temas, la app saca uno al azar y se
practica explicarlo con sus propias palabras durante un tiempo elegido."""

import random
from datetime import datetime
from app import db

# Tiempos rápidos para explicar (en minutos); también se puede escribir otro
TIEMPOS_MINUTOS = [1, 2, 3, 5, 10]
MINUTOS_MAXIMOS = 60

# Temas para empezar de un clic cuando la lista está vacía
TEMAS_SUGERIDOS = [
    'Qué es la fotosíntesis',
    'Cómo funciona internet',
    'Por qué es importante dormir bien',
    'Qué es una variable en programación',
    'Cómo se forma la lluvia',
    'Qué es la inflación',
    'Mi película favorita y por qué',
    'Cómo funciona el corazón',
    'Qué haría si fuera presidente',
    'Un hábito que quiero construir',
]


class TemaExplicar(db.Model):
    __tablename__ = 'temas_explicar'

    idTema = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    notas = db.Column(db.String(500), nullable=True)  # pistas para guiar la explicación
    vecesSalido = db.Column(db.Integer, nullable=False, default=0)
    ultimaVez = db.Column(db.DateTime, nullable=True)
    # Una vez explicado sale de la lista y de la ruleta (se puede volver a poner)
    estudiado = db.Column(db.Boolean, nullable=False, default=False)
    fechaEstudiado = db.Column(db.DateTime, nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    sesiones = db.relationship('SesionExplicacion', backref='tema', cascade='all, delete-orphan')


class SesionExplicacion(db.Model):
    """Una vez que se explicó un tema: cuánto tiempo se eligió, cuánto se habló
    y cómo se calificó la persona (1 a 5 estrellas)."""
    __tablename__ = 'sesiones_explicacion'

    idSesion = db.Column(db.Integer, primary_key=True)
    idTema = db.Column(db.Integer, db.ForeignKey('temas_explicar.idTema'), nullable=False)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    segundosObjetivo = db.Column(db.Integer, nullable=False)
    segundosHablados = db.Column(db.Integer, nullable=False)
    calificacion = db.Column(db.Integer, nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.now)

    def tiempo_texto(self):
        minutos, segundos = divmod(self.segundosHablados, 60)
        return f"{minutos}:{segundos:02d}"


def elegir_tema(temas, anterior_id=None, azar=random):
    """Saca un tema al azar, sin repetir el anterior si hay más de uno.
    Los temas que han salido menos veces tienen más probabilidad."""
    if not temas:
        return None
    opciones = [t for t in temas if t.idTema != anterior_id] or list(temas)
    menos = min(t.vecesSalido for t in opciones)
    pesos = [3 if t.vecesSalido == menos else 1 for t in opciones]
    return azar.choices(opciones, weights=pesos, k=1)[0]
