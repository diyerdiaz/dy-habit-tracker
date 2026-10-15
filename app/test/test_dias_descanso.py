from datetime import date, timedelta
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.gamificacion import calcular_racha, aplicar_penalizaciones_pendientes, get_or_create_progress
from app.level_config import PENALIZACION_POR_DIA_PERDIDO

HOY = date.today()


def _habit(user, dias, nombre='Ejercicio'):
    habit = Habit(idUser=user.idUser, habitName=nombre, habitFreq='semanal', habitCategory='salud')
    habit.set_dias(dias)
    db.session.add(habit)
    db.session.commit()
    return habit


def test_set_dias_guarda_y_lee():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud')
    h.set_dias(['4', '0', '2'])
    assert h.diasSemana == '0,2,4'
    assert h.dias_texto() == 'Lun, Mié, Vie'
    h.set_dias([])
    assert h.diasSemana is None and h.dias_texto() == 'Todos los días'


def test_toca_el_respeta_dias_y_estado():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo')
    h.set_dias([HOY.weekday()])
    assert h.toca_el(HOY)
    assert not h.toca_el(HOY + timedelta(days=1))
    h.habitState = 'Pausado'
    assert not h.toca_el(HOY)


def test_dia_de_descanso_no_rompe_la_racha(app, user):
    ayer = HOY - timedelta(days=1)
    # Toca todos los días excepto ayer
    habit = _habit(user, [d for d in range(7) if d != ayer.weekday()])
    for fecha in (HOY - timedelta(days=2), HOY):
        db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=fecha))
    db.session.commit()

    racha_actual, racha_maxima = calcular_racha(user.idUser)
    assert racha_actual == 2
    assert racha_maxima == 2


def test_dia_que_tocaba_sin_hacer_rompe_la_racha(app, user):
    habit = _habit(user, list(range(7)))
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=HOY - timedelta(days=2)))
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=HOY))
    db.session.commit()

    racha_actual, _ = calcular_racha(user.idUser)
    assert racha_actual == 1


def test_dia_de_descanso_no_resta_xp(app, user):
    # Solo toca hoy: los dos días anteriores son de descanso
    _habit(user, [HOY.weekday()])
    progress = get_or_create_progress(user.idUser)
    progress.xpTotal = 100
    progress.ultimaFechaActividad = HOY - timedelta(days=3)
    db.session.commit()

    # Días -2 y -1 son descanso; el día -3 fue de actividad pero es otro día de la semana
    assert not aplicar_penalizaciones_pendientes(progress)
    assert progress.xpTotal == 100


def test_dia_que_tocaba_sin_hacer_resta_xp(app, user):
    _habit(user, list(range(7)))
    progress = get_or_create_progress(user.idUser)
    progress.xpTotal = 100
    progress.ultimaFechaActividad = HOY - timedelta(days=2)
    db.session.commit()

    assert aplicar_penalizaciones_pendientes(progress)
    assert progress.xpTotal == 100 - PENALIZACION_POR_DIA_PERDIDO


def test_check_no_cuenta_habitos_en_descanso(logged_client, user):
    _habit(user, [d for d in range(7) if d != HOY.weekday()], nombre='Ejercicio')
    _habit(user, [], nombre='Leer')
    html = logged_client.get('/habitos/check').get_data(as_text=True)
    assert '0 / 1 completados hoy' in html
    assert 'Ejercicio' not in html
    assert '1 hábito descansa hoy' in html


def test_crear_habito_con_dias(logged_client, user):
    logged_client.post('/register_habit', data={
        'habitName': 'Gym', 'habitDesc': '', 'habitFreq': 'semanal',
        'habitCategory': 'salud', 'diasSemana': ['0', '2', '4'],
    })
    habit = Habit.query.filter_by(habitName='Gym').one()
    assert habit.dias_lista() == [0, 2, 4]
