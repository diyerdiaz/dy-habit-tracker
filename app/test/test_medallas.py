from datetime import date, timedelta
from app import db
from app.services.medallas import MEDALLAS, RANGOS, obtener_metricas, evaluar_medallas


def test_hay_130_medallas_unicas():
    assert len(MEDALLAS) == 130
    assert len({m['id'] for m in MEDALLAS}) == 130
    assert len({m['nombre'] for m in MEDALLAS}) == 130


def test_100_medallas_de_rango_20_por_rango():
    for r in RANGOS:
        del_rango = [m for m in MEDALLAS if m['rango'] == r['numero']]
        assert len(del_rango) == 20
        assert all(m['nivel_requerido'] == r['nivel'] for m in del_rango)
    assert [r['nivel'] for r in RANGOS] == [2, 4, 6, 8, 10]


def test_medallas_requiere_login(client):
    resp = client.get('/medallas/')
    assert resp.status_code == 302


def test_medallas_muestra_30_tarjetas(logged_client):
    resp = logged_client.get('/medallas/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert html.count('class="medalla-card') == 130
    assert '0</strong> de 130 desbloqueadas' in html
    assert 'Rango V · Leyenda' in html and 'Requiere nivel 10' in html


def test_boton_medallas_en_la_barra(logged_client):
    html = logged_client.get('/dashboard').get_data(as_text=True)
    assert '/medallas' in html


def test_completar_habitos_desbloquea_medallas(app, user):
    from app.models.habitos import Habit
    from app.models.hist_habits import HistHabit

    habit = Habit(idUser=user.idUser, habitName='Leer', habitFreq='Diario', habitCategory='Salud')
    db.session.add(habit)
    db.session.commit()
    hoy = date.today()
    for i in range(3):
        db.session.add(HistHabit(idUser=user.idUser, idHabit=habit.idHabit, fecha=hoy - timedelta(days=i)))
    db.session.commit()

    ganadas = {m['id'] for m in evaluar_medallas(obtener_metricas(user.idUser)) if m['desbloqueada']}
    assert {'primer_paso', 'arquitecto', 'chispa'} <= ganadas
    assert 'en_marcha' not in ganadas


def test_medalla_de_rango_exige_nivel():
    medalla = next(m for m in MEDALLAS if m['id'] == 'r1_ritmo')  # 150 hábitos, nivel 2
    metricas = {m['metrica']: 0 for m in MEDALLAS}

    metricas.update(completados=150, nivel=1)
    ritmo = next(m for m in evaluar_medallas(metricas) if m['id'] == medalla['id'])
    assert ritmo['pct'] == 100 and ritmo['falta_nivel'] and not ritmo['desbloqueada']

    metricas['nivel'] = 2
    ritmo = next(m for m in evaluar_medallas(metricas) if m['id'] == medalla['id'])
    assert ritmo['desbloqueada']


def test_dias_perfectos(app, user):
    from app.models.habitos import Habit
    from app.models.hist_habits import HistHabit
    from datetime import datetime

    hoy = date.today()
    a = Habit(idUser=user.idUser, habitName='A', habitFreq='diario', habitCategory='salud',
              createdAt=datetime.now() - timedelta(days=10))
    b = Habit(idUser=user.idUser, habitName='B', habitFreq='diario', habitCategory='salud',
              createdAt=datetime.now() - timedelta(days=10))
    db.session.add_all([a, b])
    db.session.commit()
    # Día 1: ambos (perfecto). Día 2: solo A (no perfecto).
    db.session.add_all([
        HistHabit(idUser=user.idUser, idHabit=a.idHabit, fecha=hoy - timedelta(days=1)),
        HistHabit(idUser=user.idUser, idHabit=b.idHabit, fecha=hoy - timedelta(days=1)),
        HistHabit(idUser=user.idUser, idHabit=a.idHabit, fecha=hoy - timedelta(days=2)),
    ])
    db.session.commit()
    assert obtener_metricas(user.idUser)['dias_perfectos'] == 1
