"""Tabla de Gestión de Hábitos: columnas parejas en PC y tarjetas en el celular."""
import re
from app import db
from app.models.habitos import Habit


def _habit(user, nombre, categoria='salud', estado='Activo'):
    h = Habit(idUser=user.idUser, habitName=nombre, habitFreq='diario',
              habitCategory=categoria, habitState=estado)
    h.set_dias([str(d) for d in range(7)])
    db.session.add(h)
    db.session.commit()
    return h


def test_tabla_muestra_columna_estado_con_su_chip(logged_client, user):
    _habit(user, 'Ahorrar', 'finanzas', 'Pausado')
    html = logged_client.get('/register_habit').get_data(as_text=True)
    assert '<th scope="col">Estado</th>' in html
    assert 'chip-estado estado-pausado' in html
    assert html.count('<th scope="col">') == 5


def test_cada_categoria_lleva_su_color_e_icono(logged_client, user):
    _habit(user, 'Correr', 'salud')
    _habit(user, 'Leer', 'mente')
    _habit(user, 'Orar', 'otra-categoria')  # lo desconocido cae en espiritual
    html = logged_client.get('/register_habit').get_data(as_text=True)
    assert 'habit-row cat-salud' in html and 'bi-heart-pulse' in html
    assert 'habit-row cat-mente' in html and 'bi-book' in html
    assert 'habit-row cat-espiritual' in html and 'bi-people' in html


def test_nombre_largo_se_ve_completo_al_pasar_el_mouse(logged_client, user):
    _habit(user, 'Meditar en la mañana antes del trabajo')
    html = logged_client.get('/register_habit').get_data(as_text=True)
    assert 'title="Meditar en la mañana antes del trabajo"' in html


def test_filas_vacias_ocupan_las_cinco_columnas(logged_client):
    html = logged_client.get('/register_habit').get_data(as_text=True)
    assert 'id="emptyRow"' in html
    assert html.count('colspan="5"') == 2


def test_plantilla_sin_estilos_inline_fijos():
    with open('app/templates/register/index.html') as f:
        texto = f.read()
    estilos = re.findall(r'style="([^"]*)"', texto)
    # solo queda el display:none que habits.js prende y apaga
    assert estilos == ['display: none;']
    assert 'onmouseover' not in texto


def test_css_tiene_vista_de_tarjetas_para_celular():
    with open('app/static/css/habits.css') as f:
        css = f.read()
    assert '@media (max-width: 767.98px)' in css
    assert 'grid-template-areas' in css
    assert '.habits-filtros' in css and 'height: 48px' in css


def test_paginacion_activa_se_pinta_desde_el_css():
    with open('app/static/js/habits.js') as f:
        assert 'style="background' not in f.read()
    with open('app/static/css/habits.css') as f:
        assert '.page-item.active .page-link' in f.read()


def test_iconos_del_menu_en_css_compartido():
    with open('app/static/css/m.css') as f:
        assert '.sidebar-icon' in f.read()
    with open('app/static/css/dashboard.css') as f:
        assert '.sidebar-icon' not in f.read()
