from app import db
from datetime import datetime

# Juegos de vocabulario disponibles (clave guardada en la base -> nombre visible)
JUEGOS = {
    'unir': 'Unir parejas',
}


class JuegoPartida(db.Model):
    """Una ronda terminada de un juego de vocabulario."""
    __tablename__ = 'juego_partidas'
    idPartida = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False, index=True)
    juego = db.Column(db.String(20), nullable=False)
    parejas = db.Column(db.Integer, nullable=False)
    errores = db.Column(db.Integer, nullable=False, default=0)
    segundos = db.Column(db.Integer, nullable=False, default=0)
    fecha = db.Column(db.DateTime, default=datetime.now, nullable=False)

    @property
    def precision(self):
        """% de intentos acertados: 6 parejas con 2 errores = 6/8 = 75%."""
        intentos = self.parejas + self.errores
        return round(self.parejas / intentos * 100) if intentos else 0
