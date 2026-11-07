"""Pausar un hábito a mitad de mes: solo los días en pausa dejan de contar."""
from datetime import date, datetime, timedelta

from app import db
from app.models.habito_mes import HabitoMes
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.pausa_habito import PausaHabito
from app.models.plan_mensual import PlanMensual
from app.models.recuperacion import dias_perdidos
from app.services.cuentas import borrar_cuenta
from app.services.estadisticas import calendario_del_mes, estadisticas_del_mes
from app.services.gamificacion import dias_programados
from app.services.plan_habitos import cerrar_pausas, guardar_mes_anterior, pausar_o_reanudar, pausas_del_usuario

HOY = date.today()


def _habit(user, nombre='Leer', estado='Activo', creado=None):
    habit = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario',
                  habitCategory='mente', habitState=estado)
    if creado:
        habit.createdAt = creado
    db.session.add(habit)
    db.session.commit()
    return habit


def _confirmar_plan(user):
    db.session.add(PlanMensual(idUser=user.idUser, anio=HOY.year, mes=HOY.month))
    db.session.commit()


def _marcar(user, habit, *dias):
    for dia in dias:
        db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=dia))
    db.session.commit()


def _pausar(habit, dia):
    estado = pausar_o_reanudar(habit, dia)
    db.session.commit()
    return estado


def _del_habito(stats, habit):
    return next(h for h in stats['habitos'] if h['id'] == habit.idHabit)


# ── Gestión de hábitos con el plan del mes cerrado ──

def test_usuario_pausa_con_el_plan_cerrado(logged_client, user):
    habit = _habit(user)
    _confirmar_plan(user)
    resp = logged_client.post(f'/habit/{habit.idHabit}/pausar', follow_redirects=True)
    assert 'quedó pausado' in resp.get_data(as_text=True)
    assert db.session.get(Habit, habit.idHabit).habitState == 'Pausado'
    pausa = PausaHabito.query.filter_by(idHabit=habit.idHabit).one()
    assert pausa.desde == HOY and pausa.hasta is None


def test_usuario_reanuda_lo_que_pauso_con_el_plan_cerrado(logged_client, user):
    habit = _habit(user)
    _confirmar_plan(user)
    logged_client.post(f'/habit/{habit.idHabit}/pausar')
    resp = logged_client.post(f'/habit/{habit.idHabit}/pausar', follow_redirects=True)
    assert 'se reanudó' in resp.get_data(as_text=True)
    assert db.session.get(Habit, habit.idHabit).habitState == 'Activo'
    # Pausado y reanudado el mismo día: no queda ninguna pausa
    assert PausaHabito.query.count() == 0


def test_con_el_plan_cerrado_no_se_reanuda_un_habito_que_el_plan_dejo_fuera(logged_client, user):
    fuera = _habit(user, estado='Pausado')
    _confirmar_plan(user)
    resp = logged_client.post(f'/habit/{fuera.idHabit}/pausar', follow_redirects=True)
    assert 'está cerrado' in resp.get_data(as_text=True)
    assert db.session.get(Habit, fuera.idHabit).habitState == 'Pausado'


def test_sin_plan_se_puede_reanudar_cualquiera(logged_client, user):
    fuera = _habit(user, estado='Pausado')
    logged_client.post(f'/habit/{fuera.idHabit}/pausar')
    assert db.session.get(Habit, fuera.idHabit).habitState == 'Activo'


def test_con_el_plan_cerrado_no_se_crea_ni_elimina(logged_client, user):
    habit = _habit(user)
    _confirmar_plan(user)
    logged_client.post('/register_habit', data={'habitName': 'Nuevo', 'habitFreq': 'diario', 'habitCategory': 'mente'})
    logged_client.post(f'/habit/{habit.idHabit}/delete')
    assert Habit.query.filter_by(habitName='Nuevo').first() is None
    assert db.session.get(Habit, habit.idHabit).habitState == 'Activo'


def test_completado_no_se_pausa(logged_client, user):
    habit = _habit(user, estado='Completado')
    logged_client.post(f'/habit/{habit.idHabit}/pausar')
    assert db.session.get(Habit, habit.idHabit).habitState == 'Completado'


def test_no_se_pausa_el_habito_de_otro(logged_client, user, other_user):
    ajeno = _habit(other_user)
    assert logged_client.post(f'/habit/{ajeno.idHabit}/pausar').status_code == 404
    assert db.session.get(Habit, ajeno.idHabit).habitState == 'Activo'


def test_pagina_con_plan_cerrado_muestra_pausar_pero_no_editar_ni_eliminar(logged_client, user):
    activo = _habit(user, 'Leer')
    pausado_aqui = _habit(user, 'Correr')
    _habit(user, 'Fuera del plan', estado='Pausado')
    _confirmar_plan(user)
    logged_client.post(f'/habit/{pausado_aqui.idHabit}/pausar')
    html = logged_client.get('/register_habit').get_data(as_text=True)
    assert f'/habit/{activo.idHabit}/pausar' in html
    assert html.count('accion-reanudar') == 1   # el que el plan dejó fuera no se puede reanudar
    assert 'accion-editar' not in html and 'accion-eliminar' not in html
    assert 'Registrar un Nuevo Hábito' not in html


# ── Estadísticas: solo los días en pausa dejan de contar ──

def test_dias_antes_de_la_pausa_siguen_contando(app, user):
    habit = _habit(user, creado=datetime(2026, 10, 1))
    _marcar(user, habit, *(date(2026, 11, d) for d in range(1, 6)))
    _pausar(habit, date(2026, 11, 10))
    stats = estadisticas_del_mes(user.idUser, 2026, 11, hoy=date(2026, 11, 15))
    h = _del_habito(stats, habit)
    assert h['programados'] == 9 and h['cumplidos'] == 5   # del 1 al 9; del 10 en adelante, en pausa


def test_al_reanudar_vuelve_a_contar(app, user):
    habit = _habit(user, creado=datetime(2026, 10, 1))
    _pausar(habit, date(2026, 11, 10))
    _pausar(habit, date(2026, 11, 13))
    assert db.session.get(Habit, habit.idHabit).habitState == 'Activo'
    stats = estadisticas_del_mes(user.idUser, 2026, 11, hoy=date(2026, 11, 15))
    assert _del_habito(stats, habit)['programados'] == 12   # 1–9 y 13–15
    assert pausas_del_usuario(user.idUser) == {habit.idHabit: [(date(2026, 11, 10), date(2026, 11, 12))]}


def test_calendario_no_muestra_pendientes_en_dias_pausados(app, user):
    habit = _habit(user, creado=datetime(2026, 10, 1))
    _pausar(habit, date(2026, 11, 10))
    calendario = calendario_del_mes(user.idUser, 2026, 11, hoy=date(2026, 11, 15))
    dias = {d['fecha']: d for semana in calendario['semanas'] for d in semana if not d.get('fuera')}
    assert dias[date(2026, 11, 5)]['pendientes'] == ['Leer']
    assert dias[date(2026, 11, 12)]['pendientes'] == []


def test_dias_pausados_no_rompen_la_racha_ni_se_penalizan(app, user):
    habit = _habit(user, creado=datetime(2026, 10, 1))
    _pausar(habit, date(2026, 11, 10))
    tocaba = dias_programados(user.idUser)
    assert tocaba(date(2026, 11, 5)) and not tocaba(date(2026, 11, 12))


def test_dias_pausados_no_son_dias_perdidos(app, user):
    habit = _habit(user, creado=datetime(2026, 10, 1))
    pausas = [(date(2026, 11, 10), date(2026, 11, 12))]
    perdidos = dias_perdidos(habit, set(), hoy=date(2026, 11, 15), pausas=pausas)
    assert date(2026, 11, 9) in perdidos and date(2026, 11, 13) in perdidos
    assert not any(date(2026, 11, d) in perdidos for d in (10, 11, 12))


def test_pausa_que_cruza_de_mes(app, user):
    habit = _habit(user, creado=datetime(2026, 10, 1))
    _pausar(habit, date(2026, 11, 10))
    # Diciembre: se confirma el plan nuevo y la pausa termina el 30 de noviembre
    diciembre = date(2026, 12, 2)
    guardar_mes_anterior(habit, diciembre)
    cerrar_pausas([habit], diciembre)
    db.session.commit()
    fila = HabitoMes.query.filter_by(idHabit=habit.idHabit, anio=2026, mes=11).one()
    assert fila.habitState == 'Activo'
    assert PausaHabito.query.one().hasta == date(2026, 11, 30)
    stats = estadisticas_del_mes(user.idUser, 2026, 11, hoy=diciembre)
    assert _del_habito(stats, habit)['programados'] == 9


def test_confirmar_el_plan_cierra_las_pausas_abiertas(logged_client, user):
    habit = _habit(user, creado=datetime.now() - timedelta(days=60))
    db.session.add(PausaHabito(idUser=user.idUser, idHabit=habit.idHabit, desde=HOY.replace(day=1) - timedelta(days=5)))
    habit.habitState = 'Pausado'
    db.session.commit()
    logged_client.post('/habitos/plan-mes', data={f'incluir_{habit.idHabit}': '1'})
    assert db.session.get(Habit, habit.idHabit).habitState == 'Activo'
    assert PausaHabito.query.one().hasta == HOY.replace(day=1) - timedelta(days=1)


def test_pausa_del_plan_sin_fechas_sigue_como_antes(app, user):
    """Un hábito que el plan dejó fuera (sin pausa guardada) no cuenta en todo el mes."""
    habit = _habit(user, estado='Pausado', creado=datetime(2026, 10, 1))
    stats = estadisticas_del_mes(user.idUser, 2026, 11, hoy=date(2026, 11, 15))
    assert all(h['id'] != habit.idHabit for h in stats['habitos'])


def test_borrar_la_cuenta_borra_sus_pausas(app, user):
    habit = _habit(user)
    _pausar(habit, HOY)
    borrar_cuenta(user)
    db.session.commit()
    assert PausaHabito.query.count() == 0
