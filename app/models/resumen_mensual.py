from app import db
from datetime import datetime


class ResumenVisto(db.Model):
    """Recuerda qué resúmenes de mes ya se le mostraron a cada usuario (salen una sola vez)."""
    __tablename__ = 'resumenes_vistos'

    idResumen = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('idUser', 'anio', 'mes', name='uq_resumen_user_mes'),
    )
