from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.users import User
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app import db
from datetime import date, timedelta
from collections import defaultdict

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nameUser = request.form['nameUser']
        passwordUser = request.form['passwordUser']
        
        if (user := User.query.filter_by(nameUser=nameUser, passwordUser=passwordUser).first()):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('auth.dashboard'))
        
        flash('Invalid credentials. Please try again.', 'danger')
    
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return render_template("login.html")

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
    completados_hoy = sum(1 for h in habits if h.idHabit in marcados_hoy)
    pct_hoy = round((completados_hoy / total_habitos * 100)) if total_habitos > 0 else 0

    if pct_hoy >= 80:
        mensaje_meta = '¡Consistencia sólida esta semana!'
    elif pct_hoy >= 50:
        mensaje_meta = 'Vas por buen camino.'
    elif pct_hoy > 0:
        mensaje_meta = 'Aún puedes completar más hoy.'
    else:
        mensaje_meta = 'Aún no marcas nada hoy.'

    # ── Racha actual (días consecutivos con actividad hasta hoy) ──
    dias_con_actividad = sorted(set(h.fecha for h in todos_hist))
    racha_actual = 0
    if dias_con_actividad:
        ultimo_dia = dias_con_actividad[-1]
        if (hoy - ultimo_dia).days <= 1:
            dias_set = set(dias_con_actividad)
            cursor = ultimo_dia
            while cursor in dias_set:
                racha_actual += 1
                cursor -= timedelta(days=1)

    if racha_actual >= 7:
        disciplina_label = 'Alta'
    elif racha_actual >= 3:
        disciplina_label = 'Media'
    else:
        disciplina_label = 'Baja'
    disciplina_pct = min(100, racha_actual * 10)

    # ── Consistencia: % de los últimos 7 días con alguna actividad ──
    dias_activos_semana = sum(1 for i in range(7) if (hoy - timedelta(days=i)) in dias_con_actividad)
    pct_consistencia = round(dias_activos_semana / 7 * 100)

    # ── Radar: % de cumplimiento hoy por categoría ──
    categorias = ['salud', 'mente', 'finanzas', 'espiritual']
    radar_labels = ['Salud', 'Mente', 'Finanzas', 'Espiritual']
    radar_data = []
    for cat in categorias:
        habs_cat = [h for h in habits if h.habitCategory == cat]
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
        {'id': h.idHabit, 'name': h.habitName, 'done': h.idHabit in marcados_hoy}
        for h in habits
    ]

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
    }
    return render_template("dashboard.html", data=data)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/pruebajs')
def pruebajs():
    example_data = {
        'title': 'Bienvenido a Flet',
        'message': 'Este es un mensaje desde Flask.'
    }
    import json
    return json.dumps(example_data)