from datetime import date
from app import db
from app.models.habitos import Habit
from app.models.plan_mensual import PlanMensual, primer_dia_mes_siguiente, nombre_mes

HOY = date.today()


def _habit(user, nombre='Leer', estado='Activo'):
    habit = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario',
                  habitCategory='mente', habitState=estado)
    db.session.add(habit)
    db.session.commit()
    return habit


def _confirmar_plan(user):
    db.session.add(PlanMensual(idUser=user.idUser, anio=HOY.year, mes=HOY.month))
    db.session.commit()


def test_primer_dia_mes_siguiente_cambia_de_anio():
    assert primer_dia_mes_siguiente(date(2026, 12, 15)) == date(2027, 1, 1)
    assert primer_dia_mes_siguiente(date(2026, 10, 20)) == date(2026, 11, 1)
    assert nombre_mes(date(2026, 10, 1)) == 'octubre'


def test_plan_del_mes_es_por_usuario_y_mes(app, user, other_user):
    _confirmar_plan(user)
    assert PlanMensual.del_mes(user.idUser) is not None
    assert PlanMensual.del_mes(other_user.idUser) is None
    assert PlanMensual.del_mes(user.idUser, primer_dia_mes_siguiente(HOY)) is None


def test_dashboard_pregunta_por_el_plan_si_no_existe(logged_client, user):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert 'id="planMesModal"' in html
    assert 'js/plan_mes.js' in html


def test_dashboard_no_pregunta_si_el_plan_ya_esta(logged_client, user):
    _confirmar_plan(user)
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert 'id="planMesModal"' not in html


def test_check_pregunta_por_el_plan_si_no_existe(logged_client, user):
    html = logged_client.get('/habitos/check').get_data(as_text=True)
    assert 'id="planMesModal"' in html


def test_confirmar_plan_activa_elegidos_y_pausa_el_resto(logged_client, user):
    leer = _habit(user, 'Leer')
    correr = _habit(user, 'Correr')
    resp = logged_client.post('/habitos/plan-mes', data={
        f'incluir_{leer.idHabit}': '1',
        f'dias_{leer.idHabit}': ['0', '2', '4'],
    })
    assert resp.status_code == 302
    assert PlanMensual.del_mes(user.idUser) is not None
    db.session.refresh(leer)
    db.session.refresh(correr)
    assert leer.habitState == 'Activo' and leer.dias_lista() == [0, 2, 4]
    assert correr.habitState == 'Pausado'


def test_plan_sin_habitos_elegidos_no_se_guarda(logged_client, user):
    _habit(user)
    logged_client.post('/habitos/plan-mes', data={})
    assert PlanMensual.del_mes(user.idUser) is None


def test_plan_confirmado_no_se_puede_volver_a_enviar(logged_client, user):
    leer = _habit(user, 'Leer')
    correr = _habit(user, 'Correr')
    logged_client.post('/habitos/plan-mes', data={f'incluir_{leer.idHabit}': '1'})
    logged_client.post('/habitos/plan-mes', data={f'incluir_{correr.idHabit}': '1'})
    db.session.refresh(correr)
    assert correr.habitState == 'Pausado'
    assert PlanMensual.query.filter_by(idUser=user.idUser).count() == 1


def test_sin_plan_se_pueden_editar_los_habitos(logged_client, user):
    habit = _habit(user)
    logged_client.post(f'/habit/{habit.idHabit}/edit', data={'habitName': 'Leer 20 min'})
    db.session.refresh(habit)
    assert habit.habitName == 'Leer 20 min'


def test_plan_confirmado_bloquea_crear(logged_client, user):
    _confirmar_plan(user)
    logged_client.post('/register_habit', data={
        'habitName': 'Nuevo', 'habitFreq': 'diario', 'habitCategory': 'salud',
    })
    assert Habit.query.filter_by(habitName='Nuevo').first() is None


def test_plan_confirmado_bloquea_editar_estado_y_borrar(logged_client, user):
    habit = _habit(user)
    _confirmar_plan(user)
    logged_client.post(f'/habit/{habit.idHabit}/edit', data={'habitName': 'Otro', 'diasSemana': ['1']})
    logged_client.post(f'/habit/{habit.idHabit}/state', data={'habitState': 'Pausado'})
    resp = logged_client.post(f'/habit/{habit.idHabit}/delete', follow_redirects=True)
    db.session.refresh(habit)
    assert habit.habitName == 'Leer'
    assert habit.habitState == 'Activo'
    assert habit.diasSemana is None
    assert db.session.get(Habit, habit.idHabit) is not None
    assert 'está cerrado' in resp.get_data(as_text=True)


def test_plan_confirmado_permite_marcar_el_habito_de_hoy(logged_client, user):
    habit = _habit(user)
    _confirmar_plan(user)
    resp = logged_client.post(f'/habit/{habit.idHabit}/toggle_today')
    assert resp.get_json()['done'] is True


def test_gestion_oculta_editar_cuando_hay_plan(logged_client, user):
    _habit(user)
    html = logged_client.get('/register_habit').get_data(as_text=True)
    assert 'title="Editar"' in html
    _confirmar_plan(user)
    html = logged_client.get('/register_habit').get_data(as_text=True)
    assert 'title="Editar"' not in html
    assert 'confirmado' in html


def test_pagina_del_plan_muestra_habitos(logged_client, user):
    _habit(user, 'Meditar')
    html = logged_client.get('/habitos/plan-mes').get_data(as_text=True)
    assert 'Meditar' in html and 'id="planForm"' in html


def test_meta_general_usa_el_color_del_tema():
    with open('app/static/css/m.css') as f:
        css = f.read()
    assert '#circleGrad stop:first-child' in css
    assert 'var(--tema-grad-1' in css.split('#circleGrad stop:first-child')[1].split('}')[0]


def test_personaje_del_sitio_valida_el_indice():
    from app.models.personajes_login import personaje_del_sitio, PERSONAJES
    assert personaje_del_sitio(1) is PERSONAJES[1]
    assert personaje_del_sitio(None) is None
    assert personaje_del_sitio(99) is None


def test_el_personaje_del_login_pregunta_por_el_plan(client, user):
    from app.models.personajes_login import PERSONAJES
    from app.test.conftest import TEST_PASSWORD
    client.get('/')
    with client.session_transaction() as s:
        s['personaje_login'] = 2
    client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD})
    html = client.get('/dashboard').get_data(as_text=True)
    aviso = html.split('id="planMesModal"')[1]
    assert PERSONAJES[2]['archivo'] in aviso
    assert 'plan-burbuja' in aviso
    assert f'¡Hola, {user.nameUser}!' in aviso


def test_el_aviso_espera_a_que_termine_la_cueva():
    with open('app/static/js/entrada_cueva.js') as f:
        assert "cueva:terminada" in f.read()
    with open('app/static/js/plan_mes.js') as f:
        assert "cueva:terminada" in f.read()
