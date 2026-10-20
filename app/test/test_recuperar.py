from datetime import date, datetime
import pytest
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.recuperacion import (
    Recuperacion, SesionRecuperacion, VECES_PARA_RECUPERAR, dias_perdidos, dia_libre, inicio_mes,
)
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

def _hice_en_dia_libre(client, habit, fecha):
    _Hoy.actual = fecha
    return client.post(f'/habit/{habit.idHabit}/sesion_recuperacion', follow_redirects=True)


def _completar(client, habit, fecha_perdida):
    return client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': fecha_perdida.isoformat()},
                       follow_redirects=True)


def test_habito_de_lunes_a_viernes_muestra_dias_perdidos(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4], 'Leer')
    _lun_a_vie_hechos(user, habit, menos={LUN_5, LUN_12})
    html = logged_client.get('/habitos/recuperar').get_data(as_text=True)
    assert '2 días perdidos este mes' in html
    assert '0/3 en días libres' in html
    assert 'en su día libre' in html  # botón para sumar hoy (sábado)


def test_habito_de_todos_los_dias_avisa_que_no_tiene_dia_libre(logged_client, user, hoy):
    habit = _habit(user, list(range(7)), 'Agua')
    html = logged_client.get('/habitos/recuperar').get_data(as_text=True)
    assert 'quítale al menos un día' in html
    _hice_en_dia_libre(logged_client, habit, SAB_17)
    assert SesionRecuperacion.query.count() == 0


def test_habito_al_dia(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4], 'Leer')
    _lun_a_vie_hechos(user, habit)
    assert 'Al día' in logged_client.get('/habitos/recuperar').get_data(as_text=True)


# ── 3 veces en días libres → 1 día completado ──

def test_tres_veces_en_dias_libres_completan_un_dia(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    progress = UserProgress(idUser=user.idUser, xpTotal=100, habitosCompletados=10)
    db.session.add(progress)
    db.session.commit()

    _hice_en_dia_libre(logged_client, habit, SAB_17)
    _hice_en_dia_libre(logged_client, habit, DOM_18)
    # Con 2 todavía no se completa
    _completar(logged_client, habit, LUN_5)
    assert Recuperacion.query.count() == 0
    assert '2/3 en días libres' in logged_client.get('/habitos/recuperar').get_data(as_text=True)

    _hice_en_dia_libre(logged_client, habit, SAB_24)
    resp = _completar(logged_client, habit, LUN_5)
    assert 'Completaste' in resp.get_data(as_text=True)

    rec = Recuperacion.query.filter_by(idHabit=habit.idHabit).one()
    assert rec.fechaPerdida == LUN_5 and rec.fechaRecuperada == SAB_24
    # Queda hecho ese día: lo usan historial y estadísticas
    assert HistHabit.query.filter_by(idHabit=habit.idHabit, fecha=LUN_5).first() is not None
    assert SesionRecuperacion.query.filter_by(idRecuperacion=rec.idRecuperacion).count() == 3
    db.session.refresh(progress)
    assert progress.xpTotal == 100 + XP_POR_HABITO
    assert progress.habitosCompletados == 11


def test_devuelve_la_penalizacion_del_dia_vacio(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    # Penalizaciones ya revisadas hasta el viernes 23: solo cuenta la devolución del lunes 5
    progress = UserProgress(idUser=user.idUser, xpTotal=100,
                            ultimaFechaActividad=date(2026, 10, 23), ultimaFechaPenalizada=date(2026, 10, 23))
    db.session.add(progress)
    db.session.commit()
    for fecha in (SAB_17, DOM_18, SAB_24):
        _hice_en_dia_libre(logged_client, habit, fecha)
    _completar(logged_client, habit, LUN_5)
    db.session.refresh(progress)
    assert progress.xpTotal == 100 + XP_POR_HABITO + PENALIZACION_POR_DIA_PERDIDO


def test_completar_restablece_la_racha(logged_client, user, hoy):
    from app.gamificacion import calcular_racha
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_12})
    racha_antes = calcular_racha(user.idUser)[1]
    for fecha in (SAB_17, DOM_18, SAB_24):
        _hice_en_dia_libre(logged_client, habit, fecha)
    _completar(logged_client, habit, LUN_12)
    assert calcular_racha(user.idUser)[1] > racha_antes


def test_para_otro_dia_hacen_falta_otras_tres(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5, LUN_12})
    for fecha in (SAB_17, DOM_18, SAB_24):
        _hice_en_dia_libre(logged_client, habit, fecha)
    _completar(logged_client, habit, LUN_5)
    _completar(logged_client, habit, LUN_12)
    assert Recuperacion.query.count() == 1


def test_no_cuenta_el_dia_que_le_toca(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    resp = _hice_en_dia_libre(logged_client, habit, LUN_19)
    assert SesionRecuperacion.query.count() == 0
    assert 'hazlo en un día que no le toque' in resp.get_data(as_text=True)


def test_un_solo_habito_por_dia(logged_client, user, hoy):
    leer = _habit(user, [0, 1, 2, 3, 4], 'Leer')
    correr = _habit(user, [0, 1, 2, 3, 4], 'Correr')
    _lun_a_vie_hechos(user, leer, menos={LUN_5})
    _lun_a_vie_hechos(user, correr, menos={LUN_5})
    _hice_en_dia_libre(logged_client, leer, SAB_17)
    resp = _hice_en_dia_libre(logged_client, correr, SAB_17)
    assert SesionRecuperacion.query.count() == 1
    assert 'Solo se puede uno por día' in resp.get_data(as_text=True)
    # Al día siguiente sí
    _hice_en_dia_libre(logged_client, correr, DOM_18)
    assert SesionRecuperacion.query.count() == 2


def test_no_cuenta_si_esta_al_dia(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit)
    _hice_en_dia_libre(logged_client, habit, SAB_17)
    assert SesionRecuperacion.query.count() == 0


def test_las_veces_del_mes_pasado_no_sirven(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    for fecha in (date(2026, 9, 26), date(2026, 9, 27)):
        db.session.add(SesionRecuperacion(idUser=user.idUser, idHabit=habit.idHabit, fecha=fecha))
    db.session.commit()
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    _hice_en_dia_libre(logged_client, habit, SAB_17)
    _completar(logged_client, habit, LUN_5)
    assert Recuperacion.query.count() == 0


def test_no_se_completa_un_dia_que_no_estaba_perdido(logged_client, user, hoy):
    habit = _habit(user, [0, 1, 2, 3, 4])
    _lun_a_vie_hechos(user, habit, menos={LUN_5})
    for fecha in (SAB_17, DOM_18, SAB_24):
        _hice_en_dia_libre(logged_client, habit, fecha)
    for fecha in ['2026-10-12', '2026-09-28', '2026-10-25', 'basura']:
        logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': fecha})
    assert Recuperacion.query.count() == 0


def test_no_se_toca_habito_de_otro_usuario(logged_client, other_user, hoy):
    habit = _habit(other_user, [0, 1])
    assert logged_client.post(f'/habit/{habit.idHabit}/sesion_recuperacion').status_code == 404
    assert logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-05'}).status_code == 404


def test_menu_lateral_tiene_recuperar_dia(logged_client, user):
    html = logged_client.get('/habitos/check').get_data(as_text=True)
    assert '/habitos/recuperar' in html and 'Recuperar Día' in html
