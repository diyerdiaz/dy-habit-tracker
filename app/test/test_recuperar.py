from datetime import date, datetime
import pytest
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.recuperacion import Recuperacion, MAX_POR_MES, dias_perdidos, dia_libre, inicio_mes
from app.level_config import XP_POR_HABITO, PENALIZACION_POR_DIA_PERDIDO
from app.models.user_progress import UserProgress

# Octubre de 2026: el 1 es jueves. "Hoy" empieza siendo sábado 17.
JUE_1 = date(2026, 10, 1)
LUN_5 = date(2026, 10, 5)
LUN_12 = date(2026, 10, 12)
SAB_17 = date(2026, 10, 17)
DOM_18 = date(2026, 10, 18)
LUN_19 = date(2026, 10, 19)
SAB_24 = date(2026, 10, 24)


class _Hoy(date):
    actual = SAB_17

    @classmethod
    def today(cls):
        return cls.actual


@pytest.fixture
def hoy(monkeypatch):
    """Fija la fecha de hoy en las rutas y en la gamificación."""
    import app.routes.habits_route as rutas
    import app.gamificacion as gamificacion
    monkeypatch.setattr(rutas, 'date', _Hoy)
    monkeypatch.setattr(gamificacion, 'date', _Hoy)
    _Hoy.actual = SAB_17
    return _Hoy


def _habit(user, dias, nombre='Correr', creado=datetime(2026, 9, 1)):
    habit = Habit(idUser=user.idUser, habitName=nombre, habitFreq='semanal',
                  habitCategory='salud', habitState='Activo', createdAt=creado)
    habit.set_dias(dias)
    db.session.add(habit)
    db.session.commit()
    return habit


def _lun_a_vie_hechos(user, habit, menos=()):
    """Marca como hechos todos los lunes a viernes de octubre antes del 17, salvo `menos`."""
    for dia in range(1, 17):
        fecha = date(2026, 10, dia)
        if fecha.weekday() < 5 and fecha not in menos:
            db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=fecha))
    db.session.commit()


def _sesion(client, habit, fecha):
    _Hoy.actual = fecha
    return client.post(f'/habit/{habit.idHabit}/sesion_recuperacion')


# ── Reglas (sin rutas) ──

def test_dias_perdidos_cuentan_todo_el_mes():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo',
              createdAt=datetime(2026, 9, 1))
    h.set_dias([0])  # solo lunes
    # Antes solo miraba la semana actual y salía "al día": ahora entra todo el mes
    assert dias_perdidos(h, set(), LUN_19) == [LUN_5, LUN_12]
    assert dias_perdidos(h, {LUN_5}, LUN_19) == [LUN_12]
    assert dias_perdidos(h, set(), JUE_1) == []


def test_dias_del_mes_pasado_no_cuentan():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo',
              createdAt=datetime(2026, 9, 1))
    h.set_dias([0])
    assert dias_perdidos(h, set(), date(2026, 11, 3)) == [date(2026, 11, 2)]
    assert inicio_mes(LUN_19) == JUE_1


def test_dias_antes_de_crear_el_habito_no_cuentan():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo',
              createdAt=datetime(2026, 10, 10, 9, 0))
    h.set_dias([0])
    assert dias_perdidos(h, set(), LUN_19) == [LUN_12]


def test_dia_libre_segun_los_dias_del_habito():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo')
    h.set_dias([0, 1, 2, 3, 4])
    assert dia_libre(h, SAB_17)
    assert not dia_libre(h, LUN_19)
    h.set_dias(list(range(7)))
    assert not dia_libre(h, SAB_17)


# ── Página ──

def _recuperar(client, habit, fecha, hoy_es=None):
    if hoy_es:
        _Hoy.actual = hoy_es
    return client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': fecha.isoformat()},
                       follow_redirects=True)


def test_habito_de_lunes_a_viernes_muestra_dias_perdidos_y_se_puede_el_sabado(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4], 'Leer')
    _lun_a_vie_hechos(user, habit, menos={LUN_5, LUN_12})
    html = logged_client.get('/habitos/recuperar').get_data(as_text=True)
    assert '2 días perdidos este mes' in html
    assert '3/3 recuperaciones este mes' in html
    assert 'Hoy es su día libre' in html
    assert 'disabled' not in html.split('value="2026-10-05"')[1].split('</button>')[0]


def test_habito_de_todos_los_dias_avisa_que_no_tiene_dia_libre(logged_client, user, hoy):
    habit = _habit(user, list(range(7)), 'Agua')
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=JUE_1))
    db.session.commit()
    html = logged_client.get('/habitos/recuperar').get_data(as_text=True)
    assert 'días perdidos este mes' in html
    assert 'quítale al menos un día' in html
    _recuperar(logged_client, habit, LUN_5)
    assert Recuperacion.query.count() == 0


def test_habito_al_dia(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4], 'Leer')
    _lun_a_vie_hechos(user, habit)
    assert 'Al día' in logged_client.get('/habitos/recuperar').get_data(as_text=True)


# ── Recuperar ──

def test_recuperar_en_dia_libre_cuenta_en_estadisticas_y_da_xp(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    progress = UserProgress(idUser=user.idUser, xpTotal=100, habitosCompletados=10)
    db.session.add(progress)
    db.session.commit()

    resp = _recuperar(logged_client, habit, LUN_5)
    assert 'Recuperaste' in resp.get_data(as_text=True)
    rec = Recuperacion.query.filter_by(idHabit=habit.idHabit).one()
    assert rec.fechaPerdida == LUN_5 and rec.fechaRecuperada == SAB_17
    # Queda como hecho ese día (lo usan historial y estadísticas)
    assert HistHabit.query.filter_by(idHabit=habit.idHabit, fecha=LUN_5).first() is not None
    db.session.refresh(progress)
    assert progress.xpTotal == 100 + XP_POR_HABITO
    assert progress.habitosCompletados == 11


def test_devuelve_la_penalizacion_del_dia_vacio(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    progress = UserProgress(idUser=user.idUser, xpTotal=100,
                            ultimaFechaActividad=date(2026, 10, 16), ultimaFechaPenalizada=date(2026, 10, 16))
    db.session.add(progress)
    db.session.commit()
    _recuperar(logged_client, habit, LUN_5)
    db.session.refresh(progress)
    assert progress.xpTotal == 100 + XP_POR_HABITO + PENALIZACION_POR_DIA_PERDIDO


def test_recuperar_restablece_la_racha(logged_client, user, hoy):
    from app.gamificacion import calcular_racha
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_12})
    racha_antes = calcular_racha(user.idUser)[1]
    _recuperar(logged_client, habit, LUN_12)
    assert calcular_racha(user.idUser)[1] > racha_antes


def test_no_se_recupera_el_dia_que_le_toca(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    resp = _recuperar(logged_client, habit, LUN_5, hoy_es=LUN_19)
    assert Recuperacion.query.count() == 0
    assert 'solo se recupera en sus días libres' in resp.get_data(as_text=True)


def test_un_solo_habito_por_dia(logged_client, user, hoy):
    leer = _habit(user, [0, 1, 2, 3, 4], 'Leer')
    correr = _habit(user, [0, 1, 2, 3, 4], 'Correr')
    _lun_a_vie_hechos(user, leer, menos={LUN_5})
    _lun_a_vie_hechos(user, correr, menos={LUN_5})
    _recuperar(logged_client, leer, LUN_5)
    resp = _recuperar(logged_client, correr, LUN_5)
    assert Recuperacion.query.count() == 1
    assert 'Solo se puede uno por día' in resp.get_data(as_text=True)
    # Al día siguiente (domingo, también libre) sí
    _recuperar(logged_client, correr, LUN_5, hoy_es=DOM_18)
    assert Recuperacion.query.count() == 2


def test_maximo_tres_veces_por_habito_al_mes(logged_client, user, hoy):
    habit = _habit(user, [0])  # solo lunes: martes a domingo son libres
    perdidos = [LUN_5, LUN_12, LUN_19, date(2026, 10, 26)]
    dias_libres = [date(2026, 10, 27), date(2026, 10, 28), date(2026, 10, 29), date(2026, 10, 30)]
    for perdido, libre in zip(perdidos, dias_libres):
        resp = _recuperar(logged_client, habit, perdido, hoy_es=libre)
    assert Recuperacion.query.filter_by(idHabit=habit.idHabit).count() == MAX_POR_MES
    assert 'veces este mes' in resp.get_data(as_text=True)
    # En noviembre vuelve a tener 3
    _Hoy.actual = date(2026, 11, 3)
    html = logged_client.get('/habitos/recuperar').get_data(as_text=True)
    assert '3/3 recuperaciones este mes' in html


def test_no_se_recupera_un_dia_que_no_estaba_perdido(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    for fecha in ['2026-10-12', '2026-09-28', '2026-10-25', 'basura']:
        logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': fecha})
    assert Recuperacion.query.count() == 0


def test_no_se_toca_habito_de_otro_usuario(logged_client, other_user, hoy):
    habit = _habit(other_user, [0, 1])
    assert logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-05'}).status_code == 404


def test_menu_lateral_tiene_recuperar_dia(logged_client, user):
    html = logged_client.get('/habitos/check').get_data(as_text=True)
    assert '/habitos/recuperar' in html and 'Recuperar Día' in html
