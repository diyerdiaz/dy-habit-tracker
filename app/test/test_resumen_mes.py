from datetime import date, datetime, timedelta
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.plan_mensual import PlanMensual
from app.models.resumen_mensual import ResumenVisto
from app.services.cuentas import borrar_cuenta
from app.services.resumen_mes import (
    marcar_resumen_visto, mes_anterior, resumen_del_mes, resumen_pendiente,
)

HOY = date.today()
NOVIEMBRE = date(2026, 11, 2)


def _habito(user, nombre, creado):
    habito = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario', habitCategory='mente',
                   createdAt=datetime.combine(creado, datetime.min.time()))
    db.session.add(habito)
    db.session.commit()
    return habito


def _marcar(habito, dias):
    db.session.add_all([HistHabit(idUser=habito.idUser, idHabit=habito.idHabit, fecha=d) for d in dias])
    db.session.commit()


def _octubre(cuantos=31):
    return [date(2026, 10, d) for d in range(1, cuantos + 1)]


def _mes_pasado_con_datos(user):
    anio, mes = mes_anterior(HOY)
    inicio = date(anio, mes, 1)
    habito = _habito(user, 'Leer', inicio)
    _marcar(habito, [inicio, inicio + timedelta(days=1)])
    return anio, mes


def test_mes_anterior_cruza_el_anio():
    assert mes_anterior(date(2027, 1, 15)) == (2026, 12)
    assert mes_anterior(date(2026, 11, 1)) == (2026, 10)


def test_resumen_muestra_mejor_y_peor_habito(app, user):
    meditar = _habito(user, 'Meditar', date(2026, 10, 1))
    correr = _habito(user, 'Correr', date(2026, 10, 1))
    _marcar(meditar, _octubre())
    _marcar(correr, _octubre(10))

    resumen = resumen_del_mes(user.idUser, 2026, 10, NOVIEMBRE)

    assert resumen['mes'] == 'octubre'
    assert resumen['mejor']['nombre'] == 'Meditar' and resumen['mejor']['pct'] == 100
    assert resumen['peor']['nombre'] == 'Correr' and resumen['peor']['pct'] == 32
    assert resumen['promedio'] == 66
    assert resumen['total_cumplidos'] == 41
    assert resumen['dias_activos'] == 31 and resumen['dias_del_mes'] == 31
    assert resumen['dias_perfectos'] == 10
    assert resumen['mejor_racha'] == 31
    assert resumen['mejor_dia'] == '1 de octubre'
    assert [h['nombre'] for h in resumen['habitos']] == ['Meditar', 'Correr']


def test_grafica_trae_un_punto_por_cada_dia_del_mes(app, user):
    habito = _habito(user, 'Leer', date(2026, 10, 11))
    _marcar(habito, [date(2026, 10, 11)])

    grafica = resumen_del_mes(user.idUser, 2026, 10, NOVIEMBRE)['grafica']

    assert grafica['dias'] == list(range(1, 32))
    assert grafica['pct'][:10] == [None] * 10  # el hábito aún no existía
    assert grafica['pct'][10] == 100 and grafica['pct'][11] == 0


def test_sin_peor_habito_si_hay_uno_solo_o_quedaron_iguales(app, user):
    uno = _habito(user, 'Uno', date(2026, 10, 1))
    _marcar(uno, _octubre(5))
    assert resumen_del_mes(user.idUser, 2026, 10, NOVIEMBRE)['peor'] is None

    otro = _habito(user, 'Otro', date(2026, 10, 1))
    _marcar(otro, _octubre(5))
    assert resumen_del_mes(user.idUser, 2026, 10, NOVIEMBRE)['peor'] is None


def test_compara_con_el_mes_anterior(app, user):
    habito = _habito(user, 'Leer', date(2026, 9, 1))
    _marcar(habito, [date(2026, 9, d) for d in range(1, 16)] + _octubre())

    resumen = resumen_del_mes(user.idUser, 2026, 10, NOVIEMBRE)

    assert resumen['diferencia'] == 50 and resumen['mes_comparado'] == 'septiembre'


def test_racha_no_se_corta_por_dias_de_descanso(app, user):
    habito = _habito(user, 'Leer', date(2026, 10, 1))
    habito.diasSemana = '0,2'  # lunes y miércoles
    db.session.commit()
    _marcar(habito, [date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 12)])

    assert resumen_del_mes(user.idUser, 2026, 10, NOVIEMBRE)['mejor_racha'] == 3


def test_sin_datos_no_hay_resumen(app, user):
    assert resumen_del_mes(user.idUser, 2026, 10, NOVIEMBRE) is None
    _habito(user, 'Nuevo', NOVIEMBRE)  # se creó después de ese mes
    assert resumen_pendiente(user.idUser, NOVIEMBRE) is None


def test_resumen_sale_una_vez_por_mes_y_por_usuario(app, user, other_user):
    for persona in (user, other_user):
        _habito(persona, 'Leer', date(2026, 10, 1))

    assert resumen_pendiente(user.idUser, NOVIEMBRE) is not None
    marcar_resumen_visto(user.idUser, NOVIEMBRE)
    marcar_resumen_visto(user.idUser, NOVIEMBRE)  # repetir no falla
    db.session.commit()

    assert resumen_pendiente(user.idUser, NOVIEMBRE) is None
    assert resumen_pendiente(other_user.idUser, NOVIEMBRE) is not None
    assert resumen_pendiente(user.idUser, date(2026, 12, 2)) is not None  # el de noviembre sigue pendiente
    assert ResumenVisto.query.filter_by(idUser=user.idUser).count() == 1


def test_dashboard_muestra_el_resumen_hasta_que_se_ve(logged_client, user):
    _mes_pasado_con_datos(user)

    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert 'id="resumenMesModal"' in html
    assert 'Leer' in html and 'js/resumen_mes.js' in html and 'css/resumen_mes.css' in html
    assert 'window.RESUMEN_MES' in html

    # Mientras no se abra sigue pendiente
    assert 'id="resumenMesModal"' in logged_client.get('/dashboard').get_data(as_text=True)

    assert logged_client.post('/estadisticas/resumen-mes/visto').get_json() == {'success': True}
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert 'id="resumenMesModal"' not in html and 'js/resumen_mes.js' not in html


def test_check_tambien_muestra_el_resumen_con_chart_js(logged_client, user):
    _mes_pasado_con_datos(user)
    html = logged_client.get('/habitos/check').get_data(as_text=True)
    assert 'id="resumenMesModal"' in html and 'chart.umd.min.js' in html


def test_resumen_sale_aunque_el_plan_ya_este_confirmado(logged_client, user):
    _mes_pasado_con_datos(user)
    db.session.add(PlanMensual(idUser=user.idUser, anio=HOY.year, mes=HOY.month))
    db.session.commit()
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert 'id="resumenMesModal"' in html and 'id="planMesModal"' not in html


def test_resumen_va_antes_del_aviso_del_plan(logged_client, user):
    _mes_pasado_con_datos(user)
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert html.index('id="resumenMesModal"') < html.index('id="planMesModal"')
    plan_js = logged_client.get('/static/js/plan_mes.js').get_data(as_text=True)
    assert "'resumen:cerrado'" in plan_js


def test_nombre_del_habito_va_escapado(logged_client, user):
    anio, mes = mes_anterior(HOY)
    _habito(user, '<script>alert(1)</script>', date(anio, mes, 1))
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert '<script>alert(1)</script>' not in html


def test_visto_exige_sesion(client):
    assert client.post('/estadisticas/resumen-mes/visto').status_code == 302


def test_borrar_cuenta_borra_sus_resumenes_vistos(app, user):
    id_user = user.idUser
    marcar_resumen_visto(id_user, NOVIEMBRE)
    db.session.commit()
    borrar_cuenta(user)
    db.session.commit()
    assert ResumenVisto.query.filter_by(idUser=id_user).count() == 0
