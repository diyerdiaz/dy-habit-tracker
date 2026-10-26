"""Correo de recordatorio de cada tarea a la hora que eligió el usuario (con SMTP falso)."""
from datetime import date, datetime

from app import db
from app.services import correo
from app.models.tareas import Tarea
from app.test.test_recordatorios import smtp, SMTPFalso  # noqa: F401  (fixture)

HOY = date(2026, 10, 21)


def _tarea(user, descripcion, hora=None, fecha=HOY, completada=False):
    t = Tarea(idUser=user.idUser, descripcion=descripcion, fecha=fecha,
              horaRecordatorio=hora, completada=completada)
    db.session.add(t)
    db.session.commit()
    return t


def _con_correo(user, email='yo@test.com'):
    user.email = email
    db.session.commit()
    return user


def _cuerpo(mensaje):
    return mensaje.get_body(preferencelist=('plain',)).get_content()


def test_llega_la_hora_y_se_envia_el_correo(app, smtp, user):
    _con_correo(user)
    tarea = _tarea(user, 'Pagar el arriendo', '18:00')
    _tarea(user, 'Comprar pan')  # pendiente sin recordatorio: va como "también tienes"
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 17, 59)) == 0
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 18, 5)) == 1
    assert len(smtp.enviados) == 1
    mensaje = smtp.enviados[0]
    assert mensaje['To'] == 'yo@test.com'
    assert mensaje['Subject'] == '⏰ Recordatorio: Pagar el arriendo'
    texto = _cuerpo(mensaje)
    assert 'Pagar el arriendo (6:00 p. m.)' in texto and 'Comprar pan' in texto
    html = mensaje.get_body(preferencelist=('html',)).get_content()
    assert 'Pagar el arriendo' in html and 'cid:personaje' in html
    assert db.session.get(Tarea, tarea.idTarea).recordatorioEnviado is True


def test_no_se_envia_dos_veces(app, smtp, user):
    _con_correo(user)
    _tarea(user, 'Una vez', '08:00')
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 8, 0)) == 1
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 8, 10)) == 0
    assert len(smtp.enviados) == 1


def test_no_se_envia_si_ya_la_completo_o_es_de_otro_dia(app, smtp, user):
    _con_correo(user)
    _tarea(user, 'Hecha', '08:00', completada=True)
    _tarea(user, 'De mañana', '08:00', fecha=date(2026, 10, 22))
    _tarea(user, 'Sin hora')
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 8, 5)) == 0
    assert smtp.enviados == []


def test_fuera_de_la_ventana_no_se_envia(app, smtp, user):
    _con_correo(user)
    _tarea(user, 'Tarde', '08:00')
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(
            datetime(2026, 10, 21, 8 + correo.VENTANA_MINUTOS // 60, 1)) == 0


def test_varias_tareas_a_la_vez_van_en_un_solo_correo(app, smtp, user, other_user):
    _con_correo(user)
    _con_correo(other_user, 'otro@test.com')
    _tarea(user, 'Primera', '09:00')
    _tarea(user, 'Segunda', '09:15')
    _tarea(other_user, 'Del otro', '09:00')
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 9, 20)) == 2
    por_destino = {m['To']: m for m in smtp.enviados}
    assert por_destino['yo@test.com']['Subject'] == '⏰ Tienes 2 tareas pendientes'
    assert 'Del otro' not in _cuerpo(por_destino['yo@test.com'])
    assert por_destino['otro@test.com']['Subject'] == '⏰ Recordatorio: Del otro'


def test_sin_correo_en_el_perfil_no_se_envia(app, smtp, user):
    user.email = None
    db.session.commit()
    _tarea(user, 'X', '08:00')
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 8, 0)) == 0


def test_si_falla_el_smtp_se_reintenta(app, smtp, user):
    _con_correo(user)
    tarea = _tarea(user, 'Reintentar', '08:00')
    smtp.falla = True
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 8, 0)) == 0
    assert db.session.get(Tarea, tarea.idTarea).recordatorioEnviado is False
    smtp.falla = False
    with app.app_context():
        assert correo.enviar_recordatorios_tareas(datetime(2026, 10, 21, 8, 10)) == 1


def test_el_comando_programado_incluye_las_tareas(app, smtp, user):
    # `flask enviar-recordatorios` (el que ya corre cada pocos minutos) también envía estas
    _con_correo(user)
    _tarea(user, 'Desde el comando', '08:00')
    with app.app_context():
        assert correo.enviar_recordatorios(datetime(2026, 10, 21, 8, 0)) == 1
    assert smtp.enviados[0]['Subject'] == '⏰ Recordatorio: Desde el comando'


def test_esquema_agrega_las_columnas_de_recordatorio():
    from pathlib import Path
    texto = (Path(__file__).resolve().parent.parent / 'services' / 'esquema.py').read_text()
    assert "'tareas': {'horaRecordatorio': 'VARCHAR(5)', 'recordatorioEnviado': 'BOOLEAN NOT NULL DEFAULT FALSE'}" in texto


def test_correo_de_prueba_lo_indica_y_no_marca_nada(app, smtp, user):
    _con_correo(user)
    tarea = _tarea(user, 'Ejemplo', '08:00')
    with app.app_context():
        assert correo.enviar_tareas(user, [tarea], HOY, prueba=True) is True
    mensaje = smtp.enviados[0]
    assert mensaje['Subject'] == 'Prueba: ⏰ Recordatorio: Ejemplo'
    assert 'correo de prueba' in _cuerpo(mensaje)
    assert 'correo de prueba' in mensaje.get_body(preferencelist=('html',)).get_content()
    assert db.session.get(Tarea, tarea.idTarea).recordatorioEnviado is False
