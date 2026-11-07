"""Rol de administrador: solo ve su panel (/admin) con los usuarios y sus estadísticas."""
import os
from datetime import date, datetime, timedelta

import pytest

from app import db
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.tareas import Tarea
from app.models.users import User, ROL_ADMIN, ROL_USUARIO
from app.models.vision_board import MetaVision
from app.services import admin as servicio_admin
from app.test.conftest import TEST_PASSWORD

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


def test_usuario_entra_despues_de_que_el_admin_sale(admin_client, user):
    admin_client.post('/logout')
    respuesta = admin_client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD})
    assert respuesta.headers['Location'].endswith('/dashboard')
    assert admin_client.get('/dashboard').status_code == 200
    assert admin_client.get('/admin/').status_code == 404   # ya no es admin


def test_usuario_entra_con_la_sesion_del_admin_aun_abierta(admin_client, user):
    # Pestaña cerrada sin "Salir" o login viejo desde el botón Atrás: los datos
    # nuevos no se ignoran, se entra con la otra cuenta
    respuesta = admin_client.post('/', data={'nameUser': user.nameUser, 'passwordUser': TEST_PASSWORD})
    assert respuesta.headers['Location'].endswith('/dashboard')
    assert admin_client.get('/dashboard').status_code == 200
    assert admin_client.get('/admin/').status_code == 404


def test_clave_equivocada_no_cierra_la_sesion_del_admin(admin_client, user):
    admin_client.post('/', data={'nameUser': user.nameUser, 'passwordUser': 'mala'})
    assert admin_client.get('/admin/').status_code == 200


def test_cerrar_sesion_borra_todo_lo_de_la_sesion(admin_client):
    with admin_client.session_transaction() as s:
        s['debe_cambiar_clave'] = True
    admin_client.post('/logout')
    with admin_client.session_transaction() as s:
        assert 'debe_cambiar_clave' not in s and 'sesion_version' not in s


def test_login_no_se_guarda_en_cache(client):
    assert client.get('/').headers['Cache-Control'] == 'no-store'


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


def test_admin_sin_puntos_de_carga(admin_client):
    for url in ('/admin/', '/admin/perfil'):
        assert 'js/cargando.js' not in admin_client.get(url).get_data(as_text=True), url


def test_usuario_normal_conserva_los_puntos_de_carga(logged_client):
    for url in ('/dashboard', '/tareas/'):
        assert 'js/cargando.js' in logged_client.get(url).get_data(as_text=True), url


def test_login_conserva_los_puntos_de_carga(client):
    assert 'js/cargando.js' in client.get('/').get_data(as_text=True)


def test_envio_unico_funciona_sin_puntos_de_carga(app):
    # En el admin no se carga cargando.js: el botón no debe depender de puntosCargando
    with open(os.path.join(app.static_folder, 'js', 'envio_unico.js'), encoding='utf-8') as f:
        assert "window.puntosCargando) {" in f.read()


def test_avisos_del_admin_sin_color_del_tema(app):
    with open(os.path.join(app.static_folder, 'css', 'admin.css'), encoding='utf-8') as f:
        css = f.read()
    assert '.flash-message.alert {' in css
    bloque = css.split('.flash-message.alert {', 1)[1].split('}', 1)[0]
    assert 'background: #141418' in bloque and 'box-shadow: none' in bloque
    assert '--tema' not in bloque


def test_aviso_del_admin_usa_su_hoja_de_estilos(admin_client):
    with admin_client.session_transaction() as s:
        s['_flashes'] = [('success', 'Aviso de prueba')]
    html = admin_client.get('/admin/').get_data(as_text=True)
    assert 'Aviso de prueba' in html and 'css/admin.css' in html


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


# ── Anotar hábitos de un usuario ──

def _xp(user):
    from app.models.user_progress import UserProgress
    progreso = db.session.get(UserProgress, user.idUser)
    return progreso.xpTotal if progreso else 0


def test_admin_anota_el_habito_de_ayer(admin_client, user):
    from app.services.level_config import XP_POR_HABITO
    habito = _habito(user)
    ayer = date.today() - timedelta(days=1)
    url = f'/admin/usuarios/{user.idUser}/habitos/{habito.idHabit}/anotar'
    respuesta = admin_client.post(url, data={'fecha': ayer.isoformat()})
    assert respuesta.status_code == 302 and f'fecha={ayer.isoformat()}' in respuesta.headers['Location']
    assert HistHabit.query.filter_by(idHabit=habito.idHabit, fecha=ayer).count() == 1
    assert _xp(user) == XP_POR_HABITO
    assert servicio_admin.calcular_racha(user.idUser)[0] == 1

    # Otro clic lo quita y devuelve el XP
    admin_client.post(url, data={'fecha': ayer.isoformat()})
    assert HistHabit.query.filter_by(idHabit=habito.idHabit, fecha=ayer).count() == 0
    assert _xp(user) == 0


def test_anotar_un_dia_penalizado_devuelve_la_penalizacion(admin_client, user):
    from app.models.user_progress import UserProgress
    from app.services.level_config import XP_POR_HABITO, PENALIZACION_POR_DIA_PERDIDO
    habito = _habito(user)
    hace_3 = date.today() - timedelta(days=3)
    ayer = date.today() - timedelta(days=1)
    _marcar(user, habito, hace_3)
    db.session.add(UserProgress(idUser=user.idUser, xpTotal=100, ultimaFechaActividad=hace_3,
                                ultimaFechaPenalizada=ayer))
    db.session.commit()
    url = f'/admin/usuarios/{user.idUser}/habitos/{habito.idHabit}/anotar'
    admin_client.post(url, data={'fecha': ayer.isoformat()})
    assert _xp(user) == 100 + XP_POR_HABITO + PENALIZACION_POR_DIA_PERDIDO
    admin_client.post(url, data={'fecha': ayer.isoformat()})
    assert _xp(user) == 100


def test_anotar_no_acepta_fechas_futuras_ni_invalidas(admin_client, user):
    habito = _habito(user)
    url = f'/admin/usuarios/{user.idUser}/habitos/{habito.idHabit}/anotar'
    for fecha in [(date.today() + timedelta(days=1)).isoformat(), 'ayer', '']:
        admin_client.post(url, data={'fecha': fecha})
    assert HistHabit.query.count() == 0


def test_anotar_solo_habitos_del_usuario_y_nunca_de_un_admin(admin_client, admin, user, other_user):
    ajeno = _habito(other_user)
    hoy = date.today().isoformat()
    assert admin_client.post(f'/admin/usuarios/{user.idUser}/habitos/{ajeno.idHabit}/anotar',
                             data={'fecha': hoy}).status_code == 404
    eliminado = _habito(user, 'Viejo', estado='Eliminado')
    assert admin_client.post(f'/admin/usuarios/{user.idUser}/habitos/{eliminado.idHabit}/anotar',
                             data={'fecha': hoy}).status_code == 404
    assert admin_client.post(f'/admin/usuarios/{admin.idUser}/habitos/{ajeno.idHabit}/anotar',
                             data={'fecha': hoy}).status_code == 404
    assert HistHabit.query.count() == 0


def test_usuario_normal_no_puede_anotar_por_otro(logged_client, user, other_user):
    habito = _habito(other_user)
    respuesta = logged_client.post(f'/admin/usuarios/{other_user.idUser}/habitos/{habito.idHabit}/anotar',
                                   data={'fecha': date.today().isoformat()})
    assert respuesta.status_code == 404 and HistHabit.query.count() == 0


def test_detalle_muestra_los_habitos_del_dia_elegido(admin_client, user):
    leer = _habito(user, 'Leer')
    _habito(user, 'Correr')
    ayer = date.today() - timedelta(days=1)
    _marcar(user, leer, ayer)
    html = admin_client.get(f'/admin/usuarios/{user.idUser}?fecha={ayer.isoformat()}').get_data(as_text=True)
    assert 'Anotar hábitos' in html and f'value="{ayer.isoformat()}"' in html
    assert html.count('Quitar') == 1 and html.count('Marcar hecho') == 1
    # Una fecha futura o rota muestra hoy
    manana = (date.today() + timedelta(days=1)).isoformat()
    html = admin_client.get(f'/admin/usuarios/{user.idUser}?fecha={manana}').get_data(as_text=True)
    assert f'value="{date.today().isoformat()}"' in html


# ── Pausar y eliminar hábitos de un usuario ──

def _url_habito(user, habito, accion):
    return f'/admin/usuarios/{user.idUser}/habitos/{habito.idHabit}/{accion}'


def test_admin_pausa_y_reanuda_un_habito(admin_client, user):
    habito = _habito(user)
    respuesta = admin_client.post(_url_habito(user, habito, 'pausar'))
    assert respuesta.status_code == 302 and respuesta.headers['Location'].endswith('#habitos')
    assert db.session.get(Habit, habito.idHabit).habitState == 'Pausado'
    admin_client.post(_url_habito(user, habito, 'pausar'))
    assert db.session.get(Habit, habito.idHabit).habitState == 'Activo'


def test_pausar_no_borra_lo_marcado_ni_el_xp(admin_client, user):
    from app.services.gamificacion import get_or_create_progress
    habito = _habito(user)
    _marcar(user, habito, date.today())
    get_or_create_progress(user.idUser).xpTotal = 40
    db.session.commit()
    admin_client.post(_url_habito(user, habito, 'pausar'))
    assert HistHabit.query.filter_by(idHabit=habito.idHabit).count() == 1
    assert _xp(user) == 40


def test_admin_pausa_aunque_el_plan_del_mes_este_cerrado(admin_client, user):
    from app.models.plan_mensual import PlanMensual
    hoy = date.today()
    db.session.add(PlanMensual(idUser=user.idUser, anio=hoy.year, mes=hoy.month))
    habito = _habito(user)
    admin_client.post(_url_habito(user, habito, 'pausar'))
    assert db.session.get(Habit, habito.idHabit).habitState == 'Pausado'


def test_admin_elimina_un_habito_y_sus_dias_del_mes(admin_client, user):
    from app.services.gamificacion import get_or_create_progress
    habito = _habito(user)
    _marcar(user, habito, date.today())
    get_or_create_progress(user.idUser).xpTotal = 40
    db.session.commit()
    respuesta = admin_client.post(_url_habito(user, habito, 'eliminar'), follow_redirects=True)
    assert 'y 1 día(s) marcados este mes' in respuesta.get_data(as_text=True)
    assert db.session.get(Habit, habito.idHabit).habitState == 'Eliminado'
    assert HistHabit.query.filter_by(idHabit=habito.idHabit).count() == 0
    assert _xp(user) == 40   # el XP ganado se conserva
    # Ya no aparece para pausar, anotar ni volver a eliminar
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert 'Leer' not in html
    assert admin_client.post(_url_habito(user, habito, 'eliminar')).status_code == 404


def test_eliminar_conserva_los_meses_anteriores(app, user):
    from app.models.habito_mes import HabitoMes
    from app.services.estadisticas import estadisticas_del_mes
    hoy = date(2026, 11, 15)
    habito = _habito(user)
    habito.createdAt = datetime(2026, 9, 1)
    db.session.commit()
    for dia in (date(2026, 10, 20), date(2026, 10, 21), date(2026, 11, 2), date(2026, 11, 14)):
        _marcar(user, habito, dia)

    assert servicio_admin.eliminar_habito(habito, hoy) == 2
    fechas = sorted(r.fecha for r in HistHabit.query.filter_by(idHabit=habito.idHabit))
    assert fechas == [date(2026, 10, 20), date(2026, 10, 21)]
    # Octubre queda guardado como activo: sus estadísticas no cambian
    fila = HabitoMes.query.filter_by(idHabit=habito.idHabit, anio=2026, mes=10).one()
    assert fila.habitState == 'Activo'
    octubre = estadisticas_del_mes(user.idUser, 2026, 10, hoy=hoy)
    assert [h['cumplidos'] for h in octubre['habitos'] if h['id'] == habito.idHabit] == [2]
    # Noviembre ya no lo muestra
    noviembre = estadisticas_del_mes(user.idUser, 2026, 11, hoy=hoy)
    assert all(h['id'] != habito.idHabit for h in noviembre['habitos'])


def test_pausar_conserva_los_meses_anteriores(app, user):
    from app.models.habito_mes import HabitoMes
    hoy = date(2026, 11, 15)
    habito = _habito(user)
    habito.createdAt = datetime(2026, 9, 1)
    db.session.commit()
    assert servicio_admin.pausar_habito(habito, hoy) == 'Pausado'
    assert HabitoMes.query.filter_by(idHabit=habito.idHabit, anio=2026, mes=10).one().habitState == 'Activo'


def test_pausar_y_eliminar_solo_habitos_del_usuario_y_nunca_de_un_admin(admin_client, admin, user, other_user):
    ajeno = _habito(other_user)
    for accion in ('pausar', 'eliminar'):
        assert admin_client.post(_url_habito(user, ajeno, accion)).status_code == 404
        assert admin_client.post(_url_habito(admin, ajeno, accion)).status_code == 404
    assert db.session.get(Habit, ajeno.idHabit).habitState == 'Activo'


def test_usuario_normal_no_puede_pausar_ni_eliminar_por_otro(logged_client, user, other_user):
    habito = _habito(other_user)
    for accion in ('pausar', 'eliminar'):
        assert logged_client.post(_url_habito(other_user, habito, accion)).status_code == 404
    assert db.session.get(Habit, habito.idHabit).habitState == 'Activo'


def test_detalle_muestra_pausar_eliminar_y_confirmacion(admin_client, user):
    _habito(user, 'Leer')
    _habito(user, 'Correr', estado='Pausado')
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert 'id="habitos"' in html and html.count('Reanudar') == 1 and '>Pausar<' in html
    assert html.count('data-confirmar="¿Eliminar «') == 2 and 'js/admin.js' in html


def test_panel_del_admin_tiene_margen_en_el_celular(app):
    with open(os.path.join(app.static_folder, 'css', 'admin.css'), encoding='utf-8') as f:
        css = f.read()
    celular = css.split('@media (max-width: 600px) {')[-1]
    assert celular.lstrip().split('\n')[1].strip() == '.adm { padding-left: 16px; padding-right: 16px; }'


def test_admin_no_pausa_un_habito_completado(admin_client, user):
    completado = _habito(user, 'Maratón', estado='Completado')
    resp = admin_client.post(_url_habito(user, completado, 'pausar'), follow_redirects=True)
    assert 'no se puede pausar' in resp.get_data(as_text=True)
    assert db.session.get(Habit, completado.idHabit).habitState == 'Completado'
    html = admin_client.get(f'/admin/usuarios/{user.idUser}').get_data(as_text=True)
    assert _url_habito(user, completado, 'pausar') not in html and '>Completado<' in html
