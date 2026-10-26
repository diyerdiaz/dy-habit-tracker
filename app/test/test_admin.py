"""Rol de administrador: solo ve su panel (/admin) con los usuarios y sus estadísticas."""
from datetime import date, timedelta

import pytest

from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.tareas import Tarea
from app.models.users import User, ROL_ADMIN, ROL_USUARIO
from app.models.vision_board import MetaVision
from app.services import admin as servicio_admin

CLAVE_ADMIN = 'Admin_clave1!'


@pytest.fixture
def admin(app):
    a = User(nameUser='jefe', password=CLAVE_ADMIN, rol=ROL_ADMIN)
    db.session.add(a)
    db.session.commit()
    return a


@pytest.fixture
def admin_client(client, admin):
    client.post('/', data={'nameUser': admin.nameUser, 'passwordUser': CLAVE_ADMIN})
    return client


def _habito(user, nombre='Leer', estado='Activo'):
    h = Habit(idUser=user.idUser, habitName=nombre, habitFreq='Diario', habitCategory='Salud', habitState=estado)
    db.session.add(h)
    db.session.commit()
    return h


def _marcar(user, habito, fecha):
    db.session.add(HistHabit(idUser=user.idUser, idHabit=habito.idHabit, fecha=fecha))
    db.session.commit()


# ── Rol ──

def test_usuarios_nuevos_son_usuario_normal(client):
    client.post('/User/add', data={'nameUser': 'nuevo', 'passwordUser': 'Clave_segura1', 'rol': 'admin'})
    nuevo = User.query.filter_by(nameUser='nuevo').first()
    assert nuevo.rol == ROL_USUARIO and not nuevo.es_admin   # el formulario no puede pedir ser admin


def test_esquema_agrega_la_columna_rol():
    from pathlib import Path
    texto = (Path(__file__).resolve().parent.parent / 'services' / 'esquema.py').read_text()
    assert "'rol': \"VARCHAR(20) NOT NULL DEFAULT 'usuario'\"" in texto


# ── Acceso ──

def test_admin_entra_directo_a_su_panel(client, admin):
    respuesta = client.post('/', data={'nameUser': 'jefe', 'passwordUser': CLAVE_ADMIN}, follow_redirects=True)
    assert respuesta.request.path == '/admin/'
    assert 'Usuarios' in respuesta.get_data(as_text=True)


@pytest.mark.parametrize('url', ['/dashboard', '/tareas/', '/vision/', '/menu/ingles', '/perfil/', '/register_habit'])
def test_admin_no_ve_la_parte_de_usuario(admin_client, url):
    respuesta = admin_client.get(url)
    assert respuesta.status_code == 302 and respuesta.headers['Location'].endswith('/admin/')


def test_admin_puede_cerrar_sesion(admin_client):
    assert admin_client.post('/logout', follow_redirects=True).status_code == 200
    assert admin_client.get('/admin/').status_code == 302   # ya no hay sesión: pide login


def test_usuario_normal_no_ve_el_panel(logged_client, user):
    assert logged_client.get('/admin/').status_code == 404
    assert logged_client.get(f'/admin/usuarios/{user.idUser}').status_code == 404


def test_sin_sesion_el_panel_pide_login(client):
    assert client.get('/admin/').status_code == 302


# ── Panel ──

def test_panel_lista_usuarios_y_sus_estadisticas(admin_client, admin, user, other_user):
    user.email = 'persona@test.com'
    habito = _habito(user)
    _habito(user, 'Correr', estado='Inactivo')
    hoy = date.today()
    _marcar(user, habito, hoy)
    _marcar(user, habito, hoy - timedelta(days=1))
    db.session.add_all([
        Tarea(idUser=user.idUser, descripcion='Hecha', completada=True),
        Tarea(idUser=user.idUser, descripcion='Pendiente'),
        MetaVision(idUser=user.idUser, titulo='Viajar', imagen='a.png', cumplida=True),
    ])
    db.session.commit()

    html = admin_client.get('/admin/').get_data(as_text=True)
    assert 'test_user' in html and 'otro' in html
    assert 'jefe' not in html.split('<tbody>')[1]   # el admin no sale en la lista
    assert 'persona@test.com' not in html and 'p***na@test.com' in html   # correo oculto
    assert 'Descripción' not in html and 'Hecha' not in html   # solo números, no lo que escribió

    e = servicio_admin.estadisticas_usuario(user)
    assert (e['habitos'], e['habitos_activos'], e['marcados']) == (2, 1, 2)
    assert (e['tareas'], e['tareas_hechas'], e['metas'], e['metas_logradas']) == (2, 1, 1, 1)
    assert e['dias_activos_30'] == 2 and e['racha'] == 2 and e['dias_sin_actividad'] == 0
    assert len(e['actividad']) == 30 and e['actividad'][-1] == (hoy, True)


def test_resumen_del_panel(app, user, other_user):
    habito = _habito(user)
    _marcar(user, habito, date.today())
    habito_otro = _habito(other_user)
    _marcar(other_user, habito_otro, date.today() - timedelta(days=10))
    user.email = 'a@test.com'
    db.session.commit()
    estadisticas = [servicio_admin.estadisticas_usuario(u) for u in servicio_admin.usuarios_registrados()]
    assert servicio_admin.resumen(estadisticas) == {
        'usuarios': 2, 'activos_hoy': 1, 'activos_7': 1, 'con_correo': 1, 'marcados': 2,
    }


def test_usuario_sin_actividad(app, user):
    e = servicio_admin.estadisticas_usuario(user)
    assert e['ultima_actividad'] is None and e['dias_sin_actividad'] is None
    assert e['nivel'] == 1 and e['racha'] == 0 and e['correo'] is None


def test_detalle_de_un_usuario(admin_client, admin, user):
    habito = _habito(user)
    _marcar(user, habito, date.today())
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert 'test_user' in html and 'Actividad de los últimos 30 días' in html
    assert html.count('class="adm-dia') == 30 and html.count('adm-dia activo') == 1
    # No se puede ver el detalle de otro admin ni de un usuario que no existe
    assert admin_client.get(f'/admin/usuarios/{admin.idUser}').status_code == 404
    assert admin_client.get('/admin/usuarios/9999').status_code == 404


def test_panel_vacio(admin_client):
    assert 'Todavía no hay usuarios registrados' in admin_client.get('/admin/').get_data(as_text=True)


def test_panel_carga_su_css_minimalista(admin_client):
    html = admin_client.get('/admin/').get_data(as_text=True)
    assert 'css/admin.css' in html
    assert admin_client.get('/static/css/admin.css').status_code == 200


# ── Comando crear-admin ──

def test_crear_admin(app):
    nuevo, error = servicio_admin.crear_admin('  jefa  ', CLAVE_ADMIN)
    assert error is None and nuevo.nameUser == 'jefa' and nuevo.es_admin
    assert nuevo.check_password(CLAVE_ADMIN) and nuevo.passwordUser != CLAVE_ADMIN


def test_crear_admin_valida_nombre_y_clave(app, user):
    assert servicio_admin.crear_admin('test_user', CLAVE_ADMIN)[1].startswith("El usuario 'test_user' ya existe")
    assert 'no es segura' in servicio_admin.crear_admin('jefa', '123')[1]
    assert servicio_admin.crear_admin('', CLAVE_ADMIN)[1].startswith('Escribe un nombre')
    assert User.query.filter_by(rol=ROL_ADMIN).count() == 0
    assert db.session.get(User, user.idUser).rol == ROL_USUARIO   # el existente no se vuelve admin


def test_comando_crear_admin_pide_la_clave(app):
    resultado = app.test_cli_runner().invoke(args=['crear-admin', 'jefa'], input=f'{CLAVE_ADMIN}\n{CLAVE_ADMIN}\n')
    assert resultado.exit_code == 0, resultado.output
    assert CLAVE_ADMIN not in resultado.output   # la contraseña no se muestra
    assert User.query.filter_by(nameUser='jefa').first().es_admin

    malo = app.test_cli_runner().invoke(args=['crear-admin', 'otra'], input='debil\ndebil\n')
    assert malo.exit_code != 0 and User.query.filter_by(nameUser='otra').first() is None


# ── Bloquear ──

def _bloquear(admin_client, user):
    return admin_client.post(f'/admin/usuarios/{user.idUser}/bloquear', follow_redirects=True)


def test_admin_bloquea_y_desbloquea(admin_client, user):
    html = _bloquear(admin_client, user).get_data(as_text=True)
    assert db.session.get(User, user.idUser).bloqueado is True
    assert 'quedó bloqueado' in html and 'adm-insignia' in html
    assert 'Bloqueado' in admin_client.get('/admin/').get_data(as_text=True)
    html = _bloquear(admin_client, user).get_data(as_text=True)
    assert db.session.get(User, user.idUser).bloqueado is False and 'fue desbloqueado' in html


def test_bloqueado_no_puede_iniciar_sesion(app, client, user):
    from app.test.conftest import TEST_PASSWORD
    user.bloqueado = True
    db.session.commit()
    respuesta = client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD}, follow_redirects=True)
    assert 'Tu cuenta está bloqueada' in respuesta.get_data(as_text=True)
    assert client.get('/dashboard').status_code == 302   # no quedó con sesión
    # Con la contraseña equivocada no se revela que la cuenta existe y está bloqueada
    malo = client.post('/', data={'nameUser': user.nameUser, 'passwordUser': 'otra_Clave1'}, follow_redirects=True)
    assert 'Tu cuenta está bloqueada' not in malo.get_data(as_text=True)


def test_bloquear_cierra_la_sesion_abierta(logged_client, user):
    assert logged_client.get('/dashboard').status_code == 200
    user.bloqueado = True
    db.session.commit()
    respuesta = logged_client.get('/dashboard', follow_redirects=True)
    assert respuesta.request.path == '/' and 'Tu cuenta está bloqueada' in respuesta.get_data(as_text=True)
    assert logged_client.get('/tareas/').status_code == 302


def test_bloqueado_no_recibe_correos(app, user):
    from datetime import datetime
    from app.models.recordatorios import Recordatorio
    from app.services import correo
    user.email, user.bloqueado = 'b@test.com', True
    db.session.add(Recordatorio(idUser=user.idUser, hora='08:00'))
    db.session.add(Tarea(idUser=user.idUser, descripcion='X', horaRecordatorio='08:00'))
    db.session.commit()
    enviados = []
    original = correo.enviar_correo
    correo.enviar_correo = lambda *a, **k: enviados.append(a) or True
    try:
        correo.enviar_recordatorios(datetime.combine(date.today(), datetime.min.time()).replace(hour=8))
    finally:
        correo.enviar_correo = original
    assert enviados == []


def test_no_se_puede_bloquear_ni_eliminar_a_un_admin(admin_client, admin):
    assert admin_client.post(f'/admin/usuarios/{admin.idUser}/bloquear').status_code == 404
    assert admin_client.post(f'/admin/usuarios/{admin.idUser}/eliminar', data={'confirmar': 'jefe'}).status_code == 404
    assert db.session.get(User, admin.idUser).bloqueado is False


def test_usuario_normal_no_puede_bloquear_eliminar_ni_ver_perfil_admin(logged_client, admin, other_user):
    assert logged_client.post(f'/admin/usuarios/{other_user.idUser}/bloquear').status_code == 404
    assert logged_client.post(f'/admin/usuarios/{other_user.idUser}/eliminar', data={'confirmar': 'otro'}).status_code == 404
    assert logged_client.get('/admin/perfil').status_code == 404
    assert logged_client.post('/admin/perfil/usuario', data={'nuevo_usuario': 'x'}).status_code == 404
    assert db.session.get(User, other_user.idUser).bloqueado is False
    assert db.session.get(User, other_user.idUser) is not None


def test_eliminar_pide_escribir_el_nombre(admin_client, user):
    respuesta = admin_client.post(f'/admin/usuarios/{user.idUser}/eliminar', data={'confirmar': 'otro'}, follow_redirects=True)
    assert 'escribe exactamente su nombre' in respuesta.get_data(as_text=True)
    assert db.session.get(User, user.idUser) is not None


def test_eliminar_borra_la_cuenta_y_todos_sus_datos(app, admin_client, user, other_user, tmp_path):
    from app.models.plan_mensual import PlanMensual
    from app.models.temas import TemaExplicar, SesionExplicacion
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    carpeta = tmp_path / 'vision' / str(user.idUser)
    carpeta.mkdir(parents=True)
    (carpeta / 'foto.png').write_bytes(b'x')
    id_user = user.idUser
    habito = _habito(user)
    _marcar(user, habito, date.today())
    tema = TemaExplicar(idUser=id_user, titulo='Fotosíntesis')
    db.session.add_all([tema, Tarea(idUser=id_user, descripcion='T'), PlanMensual(idUser=id_user, anio=2026, mes=10),
                        MetaVision(idUser=id_user, titulo='Meta', imagen='foto.png')])
    db.session.commit()
    db.session.add(SesionExplicacion(idTema=tema.idTema, idUser=id_user, segundosObjetivo=60, segundosHablados=50))
    _habito(other_user, 'Del otro')

    respuesta = admin_client.post(f'/admin/usuarios/{id_user}/eliminar', data={'confirmar': 'test_user'}, follow_redirects=True)
    assert respuesta.request.path == '/admin/' and 'fueron eliminados' in respuesta.get_data(as_text=True)
    assert db.session.get(User, id_user) is None
    for modelo in (Habit, HistHabit, Tarea, MetaVision, PlanMensual, TemaExplicar, SesionExplicacion):
        assert modelo.query.filter_by(idUser=id_user).count() == 0, modelo.__name__
    assert not carpeta.exists()
    assert Habit.query.filter_by(idUser=other_user.idUser).count() == 1   # lo de otros no se toca


def test_detalle_muestra_bloquear_y_eliminar(admin_client, user):
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert f'/admin/usuarios/{user.idUser}/bloquear' in html and f'/admin/usuarios/{user.idUser}/eliminar' in html
    assert 'name="confirmar"' in html and 'name="csrf_token"' in html


def test_borrar_la_propia_cuenta_tambien_borra_vision_y_temas(app, logged_client, user, tmp_path):
    # Antes estas tablas quedaban sueltas al borrar la cuenta
    from app.models.temas import TemaExplicar
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    id_user = user.idUser
    db.session.add_all([TemaExplicar(idUser=id_user, titulo='X'), MetaVision(idUser=id_user, titulo='M', imagen='m.png')])
    db.session.commit()
    logged_client.post(f'/User/delete/{id_user}')
    assert TemaExplicar.query.filter_by(idUser=id_user).count() == 0
    assert MetaVision.query.filter_by(idUser=id_user).count() == 0


# ── Perfil del admin ──

def test_perfil_del_admin(admin_client):
    html = admin_client.get('/admin/perfil').get_data(as_text=True)
    assert 'Cambiar usuario' in html and 'Cambiar contraseña' in html and 'jefe' in html


def test_admin_cambia_su_usuario(admin_client, admin, user):
    malo = admin_client.post('/admin/perfil/usuario', data={'nuevo_usuario': 'jefazo', 'contrasena_actual': 'mala'}, follow_redirects=True)
    assert 'contraseña actual no es correcta' in malo.get_data(as_text=True)
    ocupado = admin_client.post('/admin/perfil/usuario', data={'nuevo_usuario': 'test_user', 'contrasena_actual': CLAVE_ADMIN}, follow_redirects=True)
    assert 'ya está en uso' in ocupado.get_data(as_text=True)
    assert db.session.get(User, admin.idUser).nameUser == 'jefe'

    ok = admin_client.post('/admin/perfil/usuario', data={'nuevo_usuario': 'jefazo', 'contrasena_actual': CLAVE_ADMIN}, follow_redirects=True)
    assert ok.request.path == '/admin/perfil' and 'ahora tu usuario es &#34;jefazo&#34;' in ok.get_data(as_text=True)
    assert db.session.get(User, admin.idUser).nameUser == 'jefazo'


def test_admin_cambia_su_contrasena(client, admin_client, admin):
    nueva = 'Nueva_clave9!'
    debil = admin_client.post('/admin/perfil/contrasena', data={
        'contrasena_actual': CLAVE_ADMIN, 'nueva_contrasena': '123', 'confirmar_contrasena': '123'}, follow_redirects=True)
    assert 'no es segura' in debil.get_data(as_text=True)
    distinta = admin_client.post('/admin/perfil/contrasena', data={
        'contrasena_actual': CLAVE_ADMIN, 'nueva_contrasena': nueva, 'confirmar_contrasena': 'Otra_cosa9!'}, follow_redirects=True)
    assert 'no coinciden' in distinta.get_data(as_text=True)

    ok = admin_client.post('/admin/perfil/contrasena', data={
        'contrasena_actual': CLAVE_ADMIN, 'nueva_contrasena': nueva, 'confirmar_contrasena': nueva}, follow_redirects=True)
    assert 'se cambió correctamente' in ok.get_data(as_text=True)
    assert admin_client.get('/admin/').status_code == 200   # esta sesión sigue abierta
    assert db.session.get(User, admin.idUser).check_password(nueva)


def test_nav_del_admin(admin_client):
    html = admin_client.get('/admin/').get_data(as_text=True)
    assert 'href="/admin/perfil"' in html and 'Cerrar sesión' in html


def test_borrar_cuenta_solo_borra_las_fotos_de_sus_metas(app, user):
    # Nunca se borra la carpeta entera: un archivo que no es de sus metas se queda
    import os
    from app.services.cuentas import borrar_cuenta
    carpeta = os.path.join(app.config['UPLOAD_FOLDER'], 'vision', str(user.idUser))
    os.makedirs(carpeta)
    for nombre in ('suya.png', 'otro_archivo.png'):
        open(os.path.join(carpeta, nombre), 'wb').close()
    db.session.add(MetaVision(idUser=user.idUser, titulo='M', imagen='suya.png'))
    db.session.commit()
    borrar_cuenta(user)
    db.session.commit()
    assert sorted(os.listdir(carpeta)) == ['otro_archivo.png']


def test_los_tests_nunca_usan_instance_uploads(app):
    assert 'instance' not in app.config['UPLOAD_FOLDER']


def test_admin_sin_efecto_del_mouse(admin_client):
    for url in ('/admin/', '/admin/perfil'):
        assert 'js/cursor.js' not in admin_client.get(url).get_data(as_text=True), url


def test_usuario_normal_conserva_el_efecto_del_mouse(logged_client):
    for url in ('/dashboard', '/tareas/'):
        assert 'js/cursor.js' in logged_client.get(url).get_data(as_text=True), url


def test_login_conserva_el_efecto_del_mouse(client):
    assert 'js/cursor.js' in client.get('/').get_data(as_text=True)


# ── Admin desde variables de entorno (ADMIN_USUARIO / ADMIN_CONTRASENA) ──

def test_admin_del_entorno_se_crea_al_arrancar(app):
    app.config.update(ADMIN_USUARIO='jefa', ADMIN_CONTRASENA=CLAVE_ADMIN)
    assert servicio_admin.asegurar_admin_del_entorno() == 'creado'
    jefa = User.query.filter_by(nameUser='jefa').first()
    assert jefa.es_admin and jefa.check_password(CLAVE_ADMIN)
    # Al reiniciar no se duplica ni se toca
    assert servicio_admin.asegurar_admin_del_entorno() == 'ya_existe'
    assert User.query.filter_by(nameUser='jefa').count() == 1


def test_admin_del_entorno_no_pisa_la_contrasena_cambiada_en_el_perfil(app):
    app.config.update(ADMIN_USUARIO='jefa', ADMIN_CONTRASENA=CLAVE_ADMIN)
    servicio_admin.asegurar_admin_del_entorno()
    jefa = User.query.filter_by(nameUser='jefa').first()
    jefa.cambiar_contrasena('Cambiada_en_perfil1!')
    db.session.commit()
    assert servicio_admin.asegurar_admin_del_entorno() == 'ya_existe'
    assert db.session.get(User, jefa.idUser).check_password('Cambiada_en_perfil1!')


def test_admin_del_entorno_vacio_no_hace_nada(app):
    app.config.update(ADMIN_USUARIO='', ADMIN_CONTRASENA='')
    assert servicio_admin.asegurar_admin_del_entorno() == 'sin_configurar'
    app.config.update(ADMIN_USUARIO='jefa', ADMIN_CONTRASENA='')
    assert servicio_admin.asegurar_admin_del_entorno() == 'sin_configurar'
    assert User.query.filter_by(rol=ROL_ADMIN).count() == 0


def test_admin_del_entorno_nunca_convierte_a_un_usuario_normal(app, user):
    app.config.update(ADMIN_USUARIO=user.nameUser, ADMIN_CONTRASENA=CLAVE_ADMIN)
    assert servicio_admin.asegurar_admin_del_entorno() == 'nombre_ocupado'
    assert db.session.get(User, user.idUser).rol == ROL_USUARIO


def test_admin_del_entorno_con_clave_debil_no_se_crea(app, caplog):
    app.config.update(ADMIN_USUARIO='jefa', ADMIN_CONTRASENA='debil')
    assert servicio_admin.asegurar_admin_del_entorno() == 'error'
    assert User.query.filter_by(nameUser='jefa').first() is None
    assert 'no es segura' in caplog.text and 'debil' not in caplog.text.replace('no es segura', '')


def test_variables_del_admin_en_compose_sin_valores():
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent.parent
    compose = (raiz / 'docker-compose.yml').read_text()
    assert 'ADMIN_USUARIO: ${ADMIN_USUARIO:-}' in compose and 'ADMIN_CONTRASENA: ${ADMIN_CONTRASENA:-}' in compose
    assert 'asegurar_admin_del_entorno()' in (raiz / 'run.py').read_text()
