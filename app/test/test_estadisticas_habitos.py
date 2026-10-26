from datetime import date, datetime, timedelta
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.services.estadisticas import estadisticas_del_mes, leer_mes, meses_disponibles

# Mes de prueba fijo: septiembre 2026 (1 = martes)
HOY = date(2026, 10, 15)


def _habit(user, nombre, dias=None, creado=datetime(2026, 8, 1)):
    habit = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario', habitCategory='salud', createdAt=creado)
    habit.set_dias(dias or [])
    db.session.add(habit)
    db.session.commit()
    return habit


def _marcar(user, habit, *fechas):
    for f in fechas:
        db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=f))
    db.session.commit()


def test_porcentaje_diario(app, user):
    leer = _habit(user, 'Leer')
    _marcar(user, leer, *[date(2026, 9, d) for d in range(1, 16)])  # 15 de 30 días
    stats = estadisticas_del_mes(user.idUser, 2026, 9, HOY)
    h = stats['habitos'][0]
    assert (h['programados'], h['cumplidos'], h['pct'], h['nivel']) == (30, 15, 50, 'medio')


def test_solo_cuentan_los_dias_que_tocaban(app, user):
    # Lunes, miércoles y viernes: en septiembre 2026 son 13 días
    gym = _habit(user, 'Gym', dias=[0, 2, 4])
    lunes = [date(2026, 9, d) for d in (7, 14, 21, 28)]
    domingo = date(2026, 9, 6)
    _marcar(user, gym, *lunes, domingo)
    h = estadisticas_del_mes(user.idUser, 2026, 9, HOY)['habitos'][0]
    assert h['programados'] == 13
    assert h['cumplidos'] == 4
    assert h['extra'] == 1  # el domingo cuenta como extra, no sube el %
    assert h['pct'] == round(4 / 13 * 100)


def test_cuenta_desde_que_se_creo_y_hasta_hoy(app, user):
    nuevo = _habit(user, 'Meditar', creado=datetime(2026, 10, 11))
    _marcar(user, nuevo, *[date(2026, 10, d) for d in range(11, 16)])
    h = estadisticas_del_mes(user.idUser, 2026, 10, HOY)['habitos'][0]
    assert (h['programados'], h['pct']) == (5, 100)  # del 11 al 15 de octubre

    # En septiembre todavía no existía: no aparece
    assert estadisticas_del_mes(user.idUser, 2026, 9, HOY)['habitos'] == []


def test_resumen_del_mes(app, user):
    a = _habit(user, 'A')
    b = _habit(user, 'B')
    _marcar(user, a, *[date(2026, 9, d) for d in range(1, 31)])
    _marcar(user, b, date(2026, 9, 1))
    stats = estadisticas_del_mes(user.idUser, 2026, 9, HOY)
    assert stats['mejor']['nombre'] == 'A'
    assert stats['a_mejorar']['nombre'] == 'B'
    assert stats['promedio'] == round((100 + 3) / 2)
    assert stats['dias_activos'] == 30


def test_leer_mes_valida_el_filtro():
    assert leer_mes('2026-09', HOY) == (2026, 9)
    assert leer_mes('2026-13', HOY) == (2026, 10)
    assert leer_mes('2027-01', HOY) == (2026, 10)  # meses futuros no
    assert leer_mes('basura', HOY) == (2026, 10)
    assert leer_mes(None, HOY) == (2026, 10)


def test_meses_disponibles(app, user):
    _habit(user, 'Leer', creado=datetime(2026, 8, 20))
    valores = [m['valor'] for m in meses_disponibles(user.idUser, HOY)]
    assert valores == ['2026-10', '2026-09', '2026-08']


def test_pagina_estadisticas(logged_client, user):
    leer = _habit(user, 'Leer libros', creado=datetime.now() - timedelta(days=40))
    _marcar(user, leer, date.today())
    html = logged_client.get('/estadisticas/').get_data(as_text=True)
    assert 'Leer libros' in html
    assert 'class="est-barra ' in html
    assert logged_client.get('/estadisticas/?mes=2020-01').status_code == 200


def test_estadisticas_requiere_login(client):
    assert client.get('/estadisticas/').status_code == 302


def test_boton_estadisticas_en_la_barra(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert '/estadisticas/' in html
