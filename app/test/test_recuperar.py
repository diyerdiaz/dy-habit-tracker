from datetime import date, datetime
import pytest
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.recuperacion import (
    Recuperacion, dias_perdidos, puede_recuperar_hoy, semana_completa, inicio_semana,
)
from app.models.user_progress import UserProgress

# Semana de prueba: lunes 19 a domingo 25 de octubre de 2026. "Hoy" es miércoles 21.
LUNES = date(2026, 10, 19)
MARTES = date(2026, 10, 20)
MIERCOLES = date(2026, 10, 21)
JUEVES = date(2026, 10, 22)


class _Hoy(date):
    actual = MIERCOLES

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
    _Hoy.actual = MIERCOLES
    return _Hoy


def _habit(user, dias, nombre='Correr'):
    habit = Habit(idUser=user.idUser, habitName=nombre, habitFreq='semanal',
                  habitCategory='salud', habitState='Activo', createdAt=datetime(2026, 10, 1))
    habit.set_dias(dias)
    db.session.add(habit)
    db.session.commit()
    return habit


# ── Reglas (sin rutas) ──

def test_inicio_semana_es_lunes():
    assert inicio_semana(MIERCOLES) == LUNES
    assert inicio_semana(LUNES) == LUNES


def test_dias_perdidos_solo_de_esta_semana_y_antes_de_hoy():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo',
              createdAt=datetime(2026, 10, 1))
    h.set_dias([0, 1, 4])  # lun, mar, vie
    assert dias_perdidos(h, set(), MIERCOLES) == [LUNES, MARTES]
    assert dias_perdidos(h, {LUNES}, MIERCOLES) == [MARTES]
    assert dias_perdidos(h, set(), LUNES) == []


def test_dias_antes_de_crear_el_habito_no_cuentan():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo',
              createdAt=datetime(2026, 10, 20, 9, 0))
    h.set_dias([0, 1])
    assert dias_perdidos(h, set(), MIERCOLES) == [MARTES]


def test_semana_completa_no_se_puede_recuperar():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo')
    h.set_dias(list(range(7)))
    assert semana_completa(h)
    assert not puede_recuperar_hoy(h, False, MIERCOLES)


def test_solo_se_recupera_en_dia_de_descanso_y_uno_por_dia():
    h = Habit(habitName='x', habitFreq='diario', habitCategory='salud', habitState='Activo')
    h.set_dias([0, 1])  # el miércoles descansa
    assert puede_recuperar_hoy(h, False, MIERCOLES)
    assert not puede_recuperar_hoy(h, True, MIERCOLES)
    assert not puede_recuperar_hoy(h, False, MARTES)


# ── Rutas ──

def test_pagina_recuperar_lista_dias_perdidos(logged_client, user, hoy):
    _habit(user, [0, 1], 'Correr')
    html = logged_client.get('/habitos/recuperar').get_data(as_text=True)
    assert 'Correr' in html
    assert '2 días perdidos' in html
    assert 'value="2026-10-19"' in html and 'value="2026-10-20"' in html


def test_pagina_recuperar_avisa_semana_completa(logged_client, user, hoy):
    _habit(user, list(range(7)), 'Agua')
    html = logged_client.get('/habitos/recuperar').get_data(as_text=True)
    assert 'Semana completa' in html


def test_recuperar_marca_el_dia_perdido_sin_sumar_xp(logged_client, user, hoy):
    habit = _habit(user, [0, 1])
    logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-20'})
    assert HistHabit.query.filter_by(idHabit=habit.idHabit, fecha=MARTES).first() is not None
    rec = Recuperacion.query.filter_by(idHabit=habit.idHabit).one()
    assert rec.fechaPerdida == MARTES and rec.fechaRecuperada == MIERCOLES
    assert db.session.get(UserProgress, user.idUser).xpTotal == 0


def test_recuperar_no_devuelve_la_penalizacion(logged_client, user, hoy):
    habit = _habit(user, [0, 1])
    progress = UserProgress(idUser=user.idUser, xpTotal=100,
                            ultimaFechaActividad=date(2026, 10, 18), ultimaFechaPenalizada=MARTES)
    db.session.add(progress)
    db.session.commit()
    logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-20'})
    db.session.refresh(progress)
    assert progress.xpTotal == 100


def test_recuperar_restablece_la_racha(logged_client, user, hoy):
    from app.gamificacion import calcular_racha
    habit = _habit(user, [0, 1])  # lun y mar; hoy miércoles descansa
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=LUNES))
    db.session.commit()
    assert calcular_racha(user.idUser)[0] == 0  # el martes se perdió
    logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-20'})
    assert calcular_racha(user.idUser)[0] == 2


def test_solo_un_dia_recuperado_por_habito_al_dia(logged_client, user, hoy):
    habit = _habit(user, [0, 1])
    logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-19'})
    logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-20'})
    assert Recuperacion.query.filter_by(idHabit=habit.idHabit).count() == 1
    # Al día siguiente (jueves, también de descanso) sí se recupera el otro
    _Hoy.actual = JUEVES
    logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-20'})
    assert Recuperacion.query.filter_by(idHabit=habit.idHabit).count() == 2


def test_varios_habitos_se_recuperan_el_mismo_dia(logged_client, user, hoy):
    habitos = [_habit(user, [0], f'Hábito {i}') for i in range(3)]
    for h in habitos:
        logged_client.post(f'/habit/{h.idHabit}/recuperar', data={'fecha': '2026-10-19'})
    assert Recuperacion.query.filter_by(idUser=user.idUser).count() == 3


def test_no_se_recupera_si_hoy_le_toca(logged_client, user, hoy):
    habit = _habit(user, [0, 2])  # el miércoles le toca
    logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-19'})
    assert Recuperacion.query.count() == 0


def test_no_se_recupera_semana_completa(logged_client, user, hoy):
    habit = _habit(user, list(range(7)))
    resp = logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-19'},
                              follow_redirects=True)
    assert Recuperacion.query.count() == 0
    assert 'no hay día libre' in resp.get_data(as_text=True)


def test_no_se_recupera_un_dia_que_no_estaba_perdido(logged_client, user, hoy):
    habit = _habit(user, [0, 1])
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=LUNES))
    db.session.commit()
    for fecha in ['2026-10-19', '2026-10-12', '2026-10-23', 'basura']:
        logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': fecha})
    assert Recuperacion.query.count() == 0


def test_no_se_recupera_habito_de_otro_usuario(logged_client, other_user, hoy):
    habit = _habit(other_user, [0, 1])
    resp = logged_client.post(f'/habit/{habit.idHabit}/recuperar', data={'fecha': '2026-10-20'})
    assert resp.status_code == 404


def test_menu_lateral_tiene_recuperar_dia(logged_client, user):
    html = logged_client.get('/habitos/check').get_data(as_text=True)
    assert '/habitos/recuperar' in html and 'Recuperar Día' in html
