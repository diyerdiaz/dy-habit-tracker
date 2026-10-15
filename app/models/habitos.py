from app import db
from datetime import datetime

# Índices de date.weekday(): 0 = lunes ... 6 = domingo
DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


class Habit(db.Model):
    __tablename__ = 'habits'

    idHabit = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    habitName = db.Column(db.String(120), nullable=False)
    habitDesc = db.Column(db.String(255), nullable=True)
    habitFreq = db.Column(db.String(50), nullable=False)
    habitCategory = db.Column(db.String(50), nullable=False)
    habitState = db.Column(db.String(50), default='Activo')
    # Días de la semana en que toca el hábito, p. ej. "0,2,4" (lun, mié, vie).
    # NULL = todos los días. Los días que no toca no cuentan como pendientes
    # ni afectan el puntaje.
    diasSemana = db.Column(db.String(20), nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    def dias_lista(self):
        if not self.diasSemana:
            return list(range(7))
        return sorted({int(d) for d in self.diasSemana.split(',') if d.strip().isdigit() and int(d) < 7})

    def set_dias(self, dias):
        """Recibe una lista de índices (0-6). Vacía o completa = todos los días."""
        dias = sorted({int(d) for d in dias if str(d).isdigit() and int(d) < 7})
        self.diasSemana = None if not dias or len(dias) == 7 else ','.join(map(str, dias))

    def dias_texto(self):
        dias = self.dias_lista()
        if len(dias) == 7:
            return 'Todos los días'
        return ', '.join(DIAS_SEMANA[d] for d in dias)

    def toca_el(self, fecha):
        """True si el hábito está activo y le toca ese día de la semana."""
        return self.habitState == 'Activo' and fecha.weekday() in self.dias_lista()

    def to_dict(self):
        return {
            "idHabit": self.idHabit,
            "idUser": self.idUser,
            "habitName": self.habitName,
            "habitDesc": self.habitDesc,
            "habitFreq": self.habitFreq,
            "habitCategory": self.habitCategory,
            "habitState": self.habitState,
            "diasSemana": self.dias_lista(),
            "diasTexto": self.dias_texto(),
            "createdAt": self.createdAt.strftime('%Y-%m-%d %H:%M:%S')
        }
