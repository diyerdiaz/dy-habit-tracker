from app import db
from datetime import date, datetime

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


class PlanMensual(db.Model):
    """Plan de hábitos que el usuario confirma para un mes.

    Mientras no exista el plan del mes actual, los hábitos se pueden crear,
    editar y borrar. Una vez confirmado queda bloqueado hasta el mes siguiente.
    """
    __tablename__ = 'planes_mensuales'

    idPlan = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('idUser', 'anio', 'mes', name='uq_plan_user_mes'),
    )

    @staticmethod
    def del_mes(id_user, fecha=None):
        fecha = fecha or date.today()
        return PlanMensual.query.filter_by(idUser=id_user, anio=fecha.year, mes=fecha.month).first()


def nombre_mes(fecha):
    return MESES[fecha.month - 1]


def primer_dia_mes_siguiente(fecha):
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 1)
    return date(fecha.year, fecha.month + 1, 1)
