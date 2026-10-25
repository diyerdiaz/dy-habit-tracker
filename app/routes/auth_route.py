from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.users import User, contrasena_segura
from app.models.intentos_login import IntentoLogin, MAX_FALLOS, MINUTOS_BLOQUEO
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.plan_mensual import PlanMensual, nombre_mes
from app.models.personajes_login import PERSONAJES, elegir_personaje
from app import db
from datetime import date, timedelta
from collections import defaultdict
from app.services.gamificacion import calcular_racha, dias_programados

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nameUser = (request.form.get('nameUser') or '').strip()
        passwordUser = request.form.get('passwordUser') or ''

        minutos = IntentoLogin.minutos_bloqueado(nameUser)
        if minutos:
            # Bloqueado: ni siquiera se revisa la contraseña
            flash(f"Demasiados intentos fallidos. Por seguridad espera {minutos} "
                  f"{'minuto' if minutos == 1 else 'minutos'} o recupera tu contraseña.", 'danger')
        else:
            user = User.query.filter_by(nameUser=nameUser).first()
            if user and user.check_password(passwordUser):
                IntentoLogin.limpiar(nameUser)
                login_user(user)
                # El saludo de bienvenida sale siempre justo después de iniciar sesión
                session['bienvenida'] = True
                # Toda la app toma el color del personaje que salió en el login
                session['tema_sitio'] = session.get('personaje_login', 0)
                if not contrasena_segura(passwordUser):
                    # Contraseña antigua que no cumple los requisitos: se mantiene,
                    # pero no puede usar la app hasta cambiarla (ver app/__init__.py)
                    session['debe_cambiar_clave'] = True
                    return redirect(url_for('perfil.actualizar_contrasena'))
                flash("Login successful!", "success")
                return redirect(url_for('auth.dashboard'))

            restantes = IntentoLogin.registrar_fallo(nameUser) if nameUser else MAX_FALLOS
            if restantes == 0:
                flash(f'Demasiados intentos fallidos. Por seguridad el acceso queda bloqueado '
                      f'{MINUTOS_BLOQUEO} minutos. Si olvidaste tu contraseña, recupérala.', 'danger')
            else:
                flash(f"Usuario o contraseña incorrectos. Te {'queda 1 intento' if restantes == 1 else f'quedan {restantes} intentos'} "
                      f"antes de bloquear el acceso {MINUTOS_BLOQUEO} minutos.", 'danger')

    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    # Cada vez que se carga el login aparece un personaje distinto al anterior
    indice = elegir_personaje(session.get('personaje_login'))
    session['personaje_login'] = indice
    return render_template("auth/login.html", personaje=PERSONAJES[indice])

@bp.route('/dashboard')
@login_required
def dashboard():
    habits = Habit.query.filter_by(idUser=current_user.idUser).order_by(Habit.createdAt.desc()).all()
    hoy = date.today()

    marcados_hoy = {
        h.idHabit for h in HistHabit.query.filter_by(idUser=current_user.idUser, fecha=hoy).all()
    }
    todos_hist = HistHabit.query.filter_by(idUser=current_user.idUser).all()

    total_habitos = len(habits)
    activos = sum(1 for h in habits if h.habitState == 'Activo')
    # Solo cuentan los hábitos que tocan hoy; los demás son día de descanso
    tocan_hoy = [h for h in habits if h.toca_el(hoy)]
    completados_hoy = sum(1 for h in tocan_hoy if h.idHabit in marcados_hoy)
    pct_hoy = round((completados_hoy / len(tocan_hoy) * 100)) if tocan_hoy else 0

    if pct_hoy >= 80:
        mensaje_meta = '¡Consistencia sólida esta semana!'
    elif pct_hoy >= 50:
        mensaje_meta = 'Vas por buen camino.'
    elif pct_hoy > 0:
        mensaje_meta = 'Aún puedes completar más hoy.'
    else:
        mensaje_meta = 'Aún no marcas nada hoy.'

    # ── Racha actual (los días de descanso no la cortan) ──
    dias_con_actividad = set(h.fecha for h in todos_hist)
    racha_actual, _ = calcular_racha(current_user.idUser)

    if racha_actual >= 7:
        disciplina_label = 'Alta'
    elif racha_actual >= 3:
        disciplina_label = 'Media'
    else:
        disciplina_label = 'Baja'
    disciplina_pct = min(100, racha_actual * 10)

    # ── Consistencia: % de los días que tocaba algo (últimos 7) con actividad ──
    programados = dias_programados(current_user.idUser)
    dias_semana = [hoy - timedelta(days=i) for i in range(7)]
    dias_que_tocaban = [d for d in dias_semana if d.weekday() in programados]
    dias_activos_semana = sum(1 for d in dias_que_tocaban if d in dias_con_actividad)
    pct_consistencia = round(dias_activos_semana / len(dias_que_tocaban) * 100) if dias_que_tocaban else 100

    # ── Radar: % de cumplimiento hoy por categoría ──
    categorias = ['salud', 'mente', 'finanzas', 'espiritual']
    radar_labels = ['Salud', 'Mente', 'Finanzas', 'Espiritual']
    radar_data = []
    for cat in categorias:
        habs_cat = [h for h in tocan_hoy if h.habitCategory == cat]
        if habs_cat:
            done_cat = sum(1 for h in habs_cat if h.idHabit in marcados_hoy)
            radar_data.append(round(done_cat / len(habs_cat) * 100))
        else:
            radar_data.append(0)

    # ── Barras: actividades registradas por día (últimos 7 días) ──
    day_names = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    conteo_por_dia = defaultdict(int)
    for h in todos_hist:
        conteo_por_dia[h.fecha] += 1

    week_labels = []
    week_counts = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        week_labels.append(day_names[dia.weekday()])
        week_counts.append(conteo_por_dia.get(dia, 0))
    max_count = max(week_counts) if max(week_counts, default=0) > 0 else 1
    week_data = [round(c / max_count * 100) for c in week_counts]

    habitos_hoy = [
        {'id': h.idHabit, 'name': h.habitName, 'done': h.idHabit in marcados_hoy,
         'descanso': not h.toca_el(hoy)}
        for h in habits
        # Los que no tocan hoy no se muestran (salvo que ya se hayan marcado)
        if h.toca_el(hoy) or h.idHabit in marcados_hoy
    ]

    # ── Notificaciones reales, basadas en el estado actual del usuario ──
    notificaciones = []
    pendientes_hoy = len(tocan_hoy) - completados_hoy

    if total_habitos == 0:
        notificaciones.append({
            'tipo': 'info', 'icono': 'bi-info-circle-fill', 'color': '#00bac6',
            'mensaje': 'Aún no tienes hábitos registrados. ¡Crea el primero!',
        })
    elif not tocan_hoy:
        notificaciones.append({
            'tipo': 'info', 'icono': 'bi-cup-hot-fill', 'color': '#00bac6',
            'mensaje': 'Hoy es tu día de descanso: no tienes hábitos programados.',
        })
    elif pendientes_hoy > 0:
        notificaciones.append({
            'tipo': 'warning', 'icono': 'bi-exclamation-triangle-fill', 'color': '#ffc107',
            'mensaje': f"Tienes {pendientes_hoy} hábito{'s' if pendientes_hoy != 1 else ''} pendiente{'s' if pendientes_hoy != 1 else ''} por completar hoy.",
        })
    else:
        notificaciones.append({
            'tipo': 'success', 'icono': 'bi-check-circle-fill', 'color': '#00e676',
            'mensaje': '¡Completaste todos tus hábitos de hoy!',
        })

    if total_habitos > 0 and racha_actual == 0:
        notificaciones.append({
            'tipo': 'warning', 'icono': 'bi-fire', 'color': '#ff5252',
            'mensaje': 'Tu racha se reinició. ¡Retómala hoy mismo!',
        })
    elif racha_actual >= 3:
        notificaciones.append({
            'tipo': 'success', 'icono': 'bi-lightning-charge-fill', 'color': '#ffc107',
            'mensaje': f'¡Llevas una racha activa de {racha_actual} días!',
        })

    if total_habitos > 0 and pct_consistencia < 50:
        notificaciones.append({
            'tipo': 'warning', 'icono': 'bi-graph-down-arrow', 'color': '#ff5252',
            'mensaje': f'Tu consistencia semanal bajó a {pct_consistencia}%. ¡No te rindas!',
        })
    elif pct_consistencia >= 80:
        notificaciones.append({
            'tipo': 'info', 'icono': 'bi-graph-up-arrow', 'color': '#00bac6',
            'mensaje': f'Tu consistencia semanal está en {pct_consistencia}%. ¡Vas muy bien!',
        })

    data = {
        'habitos_hoy': habitos_hoy,
        'total_habitos': total_habitos,
        'activos': activos,
        'completados_hoy': completados_hoy,
        'pct_hoy': pct_hoy,
        'mensaje_meta': mensaje_meta,
        'racha_actual': racha_actual,
        'disciplina_label': disciplina_label,
        'disciplina_pct': disciplina_pct,
        'pct_consistencia': pct_consistencia,
        'radar_labels': radar_labels,
        'radar_data': radar_data,
        'week_labels': week_labels,
        'week_data': week_data,
        'week_counts': week_counts,
        'notificaciones': notificaciones,
    }
    return render_template(
        "dashboard/index.html", data=data, recien_logueado=session.pop('bienvenida', False),
        necesita_plan=PlanMensual.del_mes(current_user.idUser) is None, mes=nombre_mes(hoy),
    )


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

