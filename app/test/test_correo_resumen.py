from datetime import date, datetime
import smtplib
from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.recordatorios import Recordatorio
from app.models.resumen_mensual import ResumenEnviado, ResumenVisto
from app.services import correo
from app.services.cuentas import borrar_cuenta

AHORA = datetime(2026, 11, 2, 8, 0)
HOY = AHORA.date()


def _preparar(user, email='persona@test.com', recordatorio=True):
    user.email = email
    habito = Habit(idUser=user.idUser, habitName='Meditar <b>', habitFreq='diario', habitCategory='mente',
                   createdAt=datetime(2026, 10, 1))
    db.session.add(habito)
    db.session.commit()
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habito.idHabit, fecha=date(2026, 10, 5)))
    if recordatorio:
        db.session.add(Recordatorio(idUser=user.idUser, hora='08:00'))
    db.session.commit()


def _capturar(monkeypatch, app):
    app.config['MAIL_ENABLED'] = True
    enviados = []

    def falso(destino, asunto, texto, html=None, imagenes=None):
        enviados.append({'destino': destino, 'asunto': asunto, 'texto': texto, 'html': html})
        return True

    monkeypatch.setattr(correo, 'enviar_correo', falso)
    return enviados


def test_resumen_sale_aunque_no_sea_la_hora_del_recordatorio(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)

    correo.enviar_recordatorios(datetime(2026, 11, 1, 6, 0))  # el recordatorio es a las 8:00

    resumenes = [c for c in enviados if 'resumen de octubre' in c['asunto']]
    assert len(resumenes) == 1
    assert resumenes[0]['destino'] == 'persona@test.com'
    assert 'Tu mejor hábito' in resumenes[0]['texto'] and 'Meditar' in resumenes[0]['html']
    assert ResumenEnviado.query.filter_by(idUser=user.idUser, anio=2026, mes=10).count() == 1


def test_primer_dia_del_mes_espera_a_la_hora_del_resumen(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)

    assert correo.enviar_resumenes_mes(datetime(2026, 11, 1, 5, 55)) == 0
    assert correo.enviar_resumenes_mes(datetime(2026, 11, 1, 6, 0)) == 1
    assert len(enviados) == 1


def test_si_no_se_ha_enviado_sale_otro_dia_del_mes(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)

    assert correo.enviar_resumenes_mes(datetime(2026, 11, 20, 3, 0)) == 1
    assert correo.enviar_resumenes_mes(datetime(2026, 11, 20, 3, 5)) == 0
    assert len(enviados) == 1


def test_resumen_por_correo_sale_una_sola_vez_al_mes(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)

    assert correo.enviar_resumen_mes(user, HOY) is True
    assert correo.enviar_resumen_mes(user, date(2026, 11, 20)) is False
    assert len(enviados) == 1


def test_correo_no_depende_de_haber_visto_la_tarjeta(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)
    db.session.add(ResumenVisto(idUser=user.idUser, anio=2026, mes=10))
    db.session.commit()

    assert correo.enviar_resumen_mes(user, HOY) is True
    assert len(enviados) == 1


def test_sin_recordatorio_no_recibe_el_resumen(app, user, monkeypatch):
    _preparar(user, recordatorio=False)
    enviados = _capturar(monkeypatch, app)
    correo.enviar_recordatorios(AHORA)
    assert enviados == []


def test_sin_correo_o_sin_datos_no_se_envia(app, user, monkeypatch):
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_resumen_mes(user, HOY) is False  # sin correo
    user.email = 'persona@test.com'
    db.session.commit()
    assert correo.enviar_resumen_mes(user, HOY) is False  # sin hábitos en octubre
    assert enviados == []


def test_si_falla_se_reintenta_en_la_proxima_ejecucion(app, user, monkeypatch):
    _preparar(user)
    app.config['MAIL_ENABLED'] = True

    def falla_resumen(destino, asunto, texto, html=None, imagenes=None):
        if 'resumen de' in asunto:
            raise smtplib.SMTPException('caído')
        return True

    monkeypatch.setattr(correo, 'enviar_correo', falla_resumen)
    correo.enviar_recordatorios(AHORA)

    assert ResumenEnviado.query.count() == 0
    assert Recordatorio.query.first().ultimoEnvio == HOY  # el recordatorio sí salió

    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_resumenes_mes(AHORA) == 1
    assert len(enviados) == 1 and ResumenEnviado.query.count() == 1


def test_varios_recordatorios_reciben_un_solo_resumen(app, user, monkeypatch):
    _preparar(user)
    db.session.add(Recordatorio(idUser=user.idUser, hora='20:00'))
    db.session.commit()
    enviados = _capturar(monkeypatch, app)
    assert correo.enviar_resumenes_mes(AHORA) == 1
    assert len(enviados) == 1


def test_nombre_del_habito_va_escapado_en_el_correo(app, user, monkeypatch):
    _preparar(user)
    enviados = _capturar(monkeypatch, app)
    correo.enviar_resumen_mes(user, HOY)
    assert 'Meditar <b>' not in enviados[0]['html']


def test_enlace_lleva_al_mes_del_resumen(app, user, monkeypatch):
    _preparar(user)
    app.config['APP_URL'] = 'https://app.test/'
    enviados = _capturar(monkeypatch, app)
    correo.enviar_resumen_mes(user, HOY)
    assert 'https://app.test/estadisticas/?mes=2026-10' in enviados[0]['html']


def test_borrar_cuenta_borra_sus_envios(app, user, monkeypatch):
    _preparar(user)
    _capturar(monkeypatch, app)
    correo.enviar_resumen_mes(user, HOY)
    borrar_cuenta(user)
    db.session.commit()
    assert ResumenEnviado.query.count() == 0
