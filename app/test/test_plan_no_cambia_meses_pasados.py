from datetime import date, datetime, timedelta
from app import db
from app.models.habito_mes import HabitoMes
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.services.cuentas import borrar_cuenta
from app.services.esquema import actualizar_esquema
from app.services.estadisticas import calendario_del_mes, estadisticas_del_mes
from app.services.gamificacion import dias_programados
from app.services.plan_habitos import dias_del_mes, guardar_mes_anterior

HOY = date.today()
FIN_MES_PASADO = HOY.replace(day=1) - timedelta(days=1)
ANIO, MES = FIN_MES_PASADO.year, FIN_MES_PASADO.month
INICIO_MES_PASADO = FIN_MES_PASADO.replace(day=1)


def _habito(user, dias, nombre='Leer'):
    habito = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario', habitCategory='mente',
                   habitState='Activo', diasSemana=dias,
                   createdAt=datetime.combine(INICIO_MES_PASADO, datetime.min.time()))
    db.session.add(habito)
    db.session.commit()
    return habito


def _lunes_del_mes_pasado():
    dia, lunes = INICIO_MES_PASADO, []
    while dia <= FIN_MES_PASADO:
        if dia.weekday() == 0:
            lunes.append(dia)
        dia += timedelta(days=1)
    return lunes


def _marcar(habito, dias):
    db.session.add_all([HistHabit(idUser=habito.idUser, idHabit=habito.idHabit, fecha=d) for d in dias])
    db.session.commit()


def test_cambiar_dias_en_el_plan_no_baja_el_mes_anterior(logged_client, user):
    habito = _habito(user, '0')  # solo lunes
    _marcar(habito, _lunes_del_mes_pasado())
    assert estadisticas_del_mes(user.idUser, ANIO, MES)['promedio'] == 100

    respuesta = logged_client.post('/habitos/plan-mes', data={
        f'incluir_{habito.idHabit}': '1', f'dias_{habito.idHabit}': ['0', '1', '2', '3', '4', '5', '6'],
    })

    assert respuesta.status_code == 302
    assert db.session.get(Habit, habito.idHabit).dias_lista() == list(range(7))
    assert estadisticas_del_mes(user.idUser, ANIO, MES)['promedio'] == 100
    pendientes = [d for s in calendario_del_mes(user.idUser, ANIO, MES)['semanas'] for d in s
                  if not d['fuera'] and d['pendientes']]
    assert pendientes == []


def test_el_mes_actual_usa_los_dias_nuevos(logged_client, user):
    habito = _habito(user, '0')
    logged_client.post(f'/habit/{habito.idHabit}/edit', data={'diasSemana': ['1']})
    assert dias_del_mes(user.idUser, [habito], HOY.year, HOY.month)[habito.idHabit] == {1}
    assert dias_del_mes(user.idUser, [habito], ANIO, MES)[habito.idHabit] == {0}


def test_pausar_en_el_plan_no_saca_el_habito_del_mes_anterior(logged_client, user):
    habito = _habito(user, '0')
    otro = _habito(user, '0', 'Correr')
    _marcar(habito, _lunes_del_mes_pasado())

    logged_client.post('/habitos/plan-mes', data={f'incluir_{otro.idHabit}': '1', f'dias_{otro.idHabit}': ['0']})

    assert db.session.get(Habit, habito.idHabit).habitState == 'Pausado'
    assert dias_del_mes(user.idUser, [habito], ANIO, MES)[habito.idHabit] == {0}
    assert dias_del_mes(user.idUser, [habito], HOY.year, HOY.month)[habito.idHabit] == set()
    nombres = [h['nombre'] for h in estadisticas_del_mes(user.idUser, ANIO, MES)['habitos']]
    assert 'Leer' in nombres


def test_cada_mes_conserva_su_plan(app, user):
    habito = _habito(user, '0')
    guardar_mes_anterior(habito, date(2027, 2, 3))  # enero: lunes
    habito.set_dias(['1'])
    guardar_mes_anterior(habito, date(2027, 4, 3))  # marzo: martes
    habito.set_dias(['2'])
    db.session.commit()

    assert dias_del_mes(user.idUser, [habito], 2027, 1)[habito.idHabit] == {0}
    assert dias_del_mes(user.idUser, [habito], 2027, 2)[habito.idHabit] == {1}
    assert dias_del_mes(user.idUser, [habito], 2027, 3)[habito.idHabit] == {1}
    assert dias_del_mes(user.idUser, [habito], 2027, 4)[habito.idHabit] == {2}


def test_segundo_cambio_del_mes_no_pisa_lo_guardado(logged_client, user):
    habito = _habito(user, '0')
    logged_client.post(f'/habit/{habito.idHabit}/edit', data={'diasSemana': ['1']})
    logged_client.post(f'/habit/{habito.idHabit}/edit', data={'diasSemana': ['2']})
    assert HabitoMes.query.filter_by(idHabit=habito.idHabit).count() == 1
    assert dias_del_mes(user.idUser, [habito], ANIO, MES)[habito.idHabit] == {0}


def test_habito_nuevo_no_guarda_mes_anterior(app, user):
    habito = _habito(user, '0')
    habito.createdAt = datetime.now()
    guardar_mes_anterior(habito)
    db.session.commit()
    assert HabitoMes.query.count() == 0


def test_racha_usa_el_plan_de_cada_mes(logged_client, user):
    habito = _habito(user, '0')
    logged_client.post(f'/habit/{habito.idHabit}/edit', data={'diasSemana': ['1']})

    tocaba = dias_programados(user.idUser)
    lunes = _lunes_del_mes_pasado()[0]
    assert tocaba(lunes) and not tocaba(lunes + timedelta(days=1))


def test_actualizar_esquema_conserva_los_meses_de_habitos_existentes(app, user):
    habito = _habito(user, '0')
    habito.habitState = 'Pausado'
    db.session.commit()
    HabitoMes.__table__.drop(db.engine)

    actualizar_esquema()

    assert dias_del_mes(user.idUser, [habito], ANIO, MES)[habito.idHabit] == {0}
    assert dias_del_mes(user.idUser, [habito], HOY.year, HOY.month)[habito.idHabit] == set()
    actualizar_esquema()  # la segunda vez no repite nada
    assert HabitoMes.query.count() == 1


def test_borrar_habito_y_cuenta_borran_sus_meses(logged_client, user):
    habito = _habito(user, '0')
    otro = _habito(user, '1', 'Correr')
    guardar_mes_anterior(habito)
    guardar_mes_anterior(otro)
    db.session.commit()

    logged_client.post(f'/habit/{habito.idHabit}/delete')
    assert HabitoMes.query.filter_by(idHabit=habito.idHabit).count() == 0

    borrar_cuenta(user)
    db.session.commit()
    assert HabitoMes.query.count() == 0
