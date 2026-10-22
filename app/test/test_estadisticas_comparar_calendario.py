from datetime import date, datetime, timedelta
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.estadisticas import (
    leer_meses, comparar_meses, calendario_del_mes, MAX_MESES_COMPARAR,
)

HOY = date(2026, 10, 15)


def _habit(user, nombre, dias=None, creado=datetime(2026, 7, 1)):
    habit = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario', habitCategory='salud', createdAt=creado)
    habit.set_dias(dias or [])
    db.session.add(habit)
    db.session.commit()
    return habit


def _marcar(user, habit, *fechas):
    for f in fechas:
        db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=f))
    db.session.commit()


# ── leer_meses ──

def test_leer_meses_ordena_y_quita_repetidos_e_invalidos():
    assert leer_meses(['2026-09', '2026-07', '2026-09', 'basura', '2027-01', '2026-13'], HOY) == [
        (2026, 7), (2026, 9)]


def test_leer_meses_por_defecto_los_ultimos_tres():
    assert leer_meses([], HOY) == [(2026, 8), (2026, 9), (2026, 10)]
    assert leer_meses(None, date(2026, 2, 3)) == [(2025, 12), (2026, 1), (2026, 2)]


def test_leer_meses_tiene_un_maximo():
    textos = [f"{a}-{m:02d}" for a in (2024, 2025) for m in range(1, 13)]
    elegidos = leer_meses(textos, HOY)
    assert len(elegidos) == MAX_MESES_COMPARAR
    assert elegidos[-1] == (2025, 12)  # se quedan los más recientes


# ── comparar_meses ──

def test_comparar_varios_meses_por_habito(app, user):
    leer = _habit(user, 'Leer')
    _marcar(user, leer, *[date(2026, 8, d) for d in range(1, 32)])   # agosto 100%
    _marcar(user, leer, *[date(2026, 9, d) for d in range(1, 16)])   # septiembre 50%

    cmp = comparar_meses(user.idUser, [(2026, 8), (2026, 9)], HOY)
    assert [m['nombre'] for m in cmp['meses']] == ['Agosto 2026', 'Septiembre 2026']
    fila = cmp['habitos'][0]
    assert fila['nombre'] == 'Leer'
    assert [v['pct'] for v in fila['valores']] == [100, 50]
    assert fila['diferencia'] == -50
    assert cmp['diferencia_promedio'] == -50


def test_comparar_tres_meses_con_habito_nuevo(app, user):
    viejo = _habit(user, 'Viejo')
    nuevo = _habit(user, 'Nuevo', creado=datetime(2026, 9, 1))
    _marcar(user, viejo, *[date(2026, 7, d) for d in range(1, 11)])
    _marcar(user, nuevo, *[date(2026, 9, d) for d in range(1, 31)])

    cmp = comparar_meses(user.idUser, [(2026, 7), (2026, 8), (2026, 9)], HOY)
    filas = {f['nombre']: f for f in cmp['habitos']}
    # El hábito nuevo no existía en julio ni agosto
    assert filas['Nuevo']['valores'][:2] == [None, None]
    assert filas['Nuevo']['valores'][2]['pct'] == 100
    assert filas['Nuevo']['diferencia'] is None  # solo un mes con datos
    assert [v['pct'] for v in filas['Viejo']['valores']] == [round(10 / 31 * 100), 0, 0]


def test_comparar_sin_habitos(app, user):
    cmp = comparar_meses(user.idUser, [(2026, 9), (2026, 10)], HOY)
    assert cmp['habitos'] == []
    assert cmp['diferencia_promedio'] is None


# ── calendario_del_mes ──

def _dias(cal):
    return {d['fecha']: d for semana in cal['semanas'] for d in semana if not d['fuera']}


def test_calendario_muestra_hechos_y_pendientes(app, user):
    leer = _habit(user, 'Leer')
    gym = _habit(user, 'Gym', dias=[0, 2, 4])  # lunes, miércoles, viernes
    _marcar(user, leer, date(2026, 9, 7), date(2026, 9, 8))
    _marcar(user, gym, date(2026, 9, 7))

    cal = calendario_del_mes(user.idUser, 2026, 9, HOY)
    dias = _dias(cal)
    assert len(dias) == 30

    lunes = dias[date(2026, 9, 7)]
    assert lunes['hechos'] == ['Gym', 'Leer']
    assert lunes['pendientes'] == []
    assert (lunes['tocaban'], lunes['pct'], lunes['nivel']) == (2, 100, 'alto')

    martes = dias[date(2026, 9, 8)]  # gym no toca los martes
    assert martes['hechos'] == ['Leer']
    assert martes['tocaban'] == 1 and martes['pct'] == 100

    miercoles = dias[date(2026, 9, 9)]
    assert miercoles['hechos'] == []
    assert sorted(miercoles['pendientes']) == ['Gym', 'Leer']
    assert miercoles['nivel'] == 'bajo'

    assert cal['total_hechos'] == 3
    assert cal['dias_con_algo'] == 2


def test_calendario_semanas_empiezan_en_lunes(app, user):
    cal = calendario_del_mes(user.idUser, 2026, 9, HOY)
    primera = cal['semanas'][0]
    assert len(primera) == 7
    assert primera[0]['fecha'].weekday() == 0
    # El 1 de septiembre de 2026 es martes: el lunes 31 de agosto va de relleno
    assert primera[0]['fuera'] and primera[0]['numero'] == 31
    assert not primera[1]['fuera'] and primera[1]['numero'] == 1


def test_calendario_dias_futuros_y_antes_de_crear(app, user):
    _habit(user, 'Meditar', creado=datetime(2026, 10, 10))
    dias = _dias(calendario_del_mes(user.idUser, 2026, 10, HOY))
    assert dias[date(2026, 10, 5)]['tocaban'] == 0      # todavía no existía
    assert dias[date(2026, 10, 12)]['pendientes'] == ['Meditar']
    futuro = dias[date(2026, 10, 20)]
    assert futuro['futuro'] and futuro['pendientes'] == [] and futuro['pct'] is None
    assert dias[HOY]['es_hoy']


def test_calendario_no_muestra_habitos_de_otro_usuario(app, user, other_user):
    ajeno = _habit(other_user, 'Ajeno')
    _marcar(other_user, ajeno, date(2026, 9, 7))
    dias = _dias(calendario_del_mes(user.idUser, 2026, 9, HOY))
    assert dias[date(2026, 9, 7)]['hechos'] == []


# ── Páginas ──

def test_pestanas_en_estadisticas(logged_client):
    html = logged_client.get('/estadisticas/').get_data(as_text=True)
    assert '/estadisticas/comparar' in html
    assert '/estadisticas/calendario' in html


def test_pagina_comparar(logged_client, user):
    leer = _habit(user, 'Leer libros', creado=datetime.now() - timedelta(days=100))
    _marcar(user, leer, date.today())
    html = logged_client.get('/estadisticas/comparar').get_data(as_text=True)
    assert 'Leer libros' in html
    assert 'Promedio general' in html
    assert html.count('class="cmp-fila"') >= 3 * 2  # 3 meses: promedio + hábito

    hoy = date.today()
    actual = f"{hoy.year}-{hoy.month:02d}"
    html = logged_client.get(f'/estadisticas/comparar?m={actual}&m=basura').get_data(as_text=True)
    assert f'value="{actual}" checked' in html


def test_atajo_ultimos_meses_envia_varios(logged_client, user):
    _habit(user, 'Leer', creado=datetime.now() - timedelta(days=100))
    html = logged_client.get('/estadisticas/comparar').get_data(as_text=True)
    assert 'Últimos 3' in html
    assert html.count('m=') >= 3


def test_pagina_calendario(logged_client, user):
    leer = _habit(user, 'Leer libros', creado=datetime.now() - timedelta(days=40))
    _marcar(user, leer, date.today())
    html = logged_client.get('/estadisticas/calendario').get_data(as_text=True)
    assert f'data-dia="{date.today().isoformat()}"' in html
    assert 'Leer libros' in html
    assert 'js/estadisticas_habitos.js' in html
    assert logged_client.get('/estadisticas/calendario?mes=2020-01').status_code == 200


def test_comparar_y_calendario_requieren_login(client):
    assert client.get('/estadisticas/comparar').status_code == 302
    assert client.get('/estadisticas/calendario').status_code == 302
