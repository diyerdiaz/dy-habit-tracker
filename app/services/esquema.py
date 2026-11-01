import logging

from sqlalchemy import inspect, text

from app import db
from app.models.habito_mes import HabitoMes
from app.models.habitos import Habit
from app.services.plan_habitos import guardar_mes_anterior

logger = logging.getLogger(__name__)


def actualizar_esquema():
    """Crea las tablas que falten y agrega columnas nuevas a bases de datos
    existentes (create_all no modifica tablas ya creadas). Nunca borra datos."""
    sin_meses_guardados = HabitoMes.__tablename__ not in inspect(db.engine).get_table_names()
    db.create_all()
    columnas_nuevas = {
        'habits': {'diasSemana': 'VARCHAR(20)'},
        'users': {'avatar': 'VARCHAR(64)', 'email': 'VARCHAR(120)', 'sesionVersion': 'INTEGER NOT NULL DEFAULT 0', 'rol': "VARCHAR(20) NOT NULL DEFAULT 'usuario'", 'bloqueado': 'BOOLEAN NOT NULL DEFAULT FALSE'},
        'metas_vision': {'ancho': 'INTEGER', 'alto': 'INTEGER'},
        'temas_explicar': {'estudiado': 'BOOLEAN NOT NULL DEFAULT FALSE', 'fechaEstudiado': 'TIMESTAMP'},
        'juego_partidas': {'nivel': 'VARCHAR(10)', 'pistas': 'INTEGER NOT NULL DEFAULT 0'},
        'tareas': {'horaRecordatorio': 'VARCHAR(5)', 'recordatorioEnviado': 'BOOLEAN NOT NULL DEFAULT FALSE'},
    }
    inspector = inspect(db.engine)
    for tabla, columnas in columnas_nuevas.items():
        existentes = {c['name'] for c in inspector.get_columns(tabla)}
        for nombre, tipo in columnas.items():
            if nombre not in existentes:
                db.session.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}'))
                logger.info("Columna %s.%s agregada", tabla, nombre)
    if sin_meses_guardados:
        # Los hábitos ya creados contaban en los meses pasados aunque hoy estén pausados
        for habit in Habit.query.all():
            guardar_mes_anterior(habit, estado='Activo')
    db.session.commit()
