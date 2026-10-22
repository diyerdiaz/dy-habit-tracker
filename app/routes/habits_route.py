from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app.models.plan_mensual import PlanMensual, nombre_mes, primer_dia_mes_siguiente
from app.models.recuperacion import (
    Recuperacion, SesionRecuperacion, VECES_PARA_RECUPERAR, dias_perdidos, dia_libre, inicio_mes,
    dias_libres_que_quedan, cuantos_se_pueden_recuperar,
)
from app import db
from app.gamificacion import registrar_toggle_habito, registrar_recuperacion
from datetime import date, timedelta
from sqlalchemy.exc import IntegrityError

bp = Blueprint('habits', __name__)


def _plan_bloqueado():
    """Si el plan del mes ya se confirmó, avisa y devuelve la redirección.
    Los hábitos no se pueden cambiar hasta el mes siguiente."""
    if not PlanMensual.del_mes(current_user.idUser):
        return None
    desbloqueo = primer_dia_mes_siguiente(date.today())
    flash(f"Tu plan de {nombre_mes(date.today())} está cerrado. "
          f"Podrás cambiar tus hábitos desde el {desbloqueo.strftime('%d/%m/%Y')}.", "warning")
    return redirect(url_for('habits.register_habit'))


@bp.route('/habitos/plan-mes', methods=['GET', 'POST'])
@login_required
def plan_mes():
    hoy = date.today()
    plan = PlanMensual.del_mes(current_user.idUser)
    habits = Habit.query.filter_by(idUser=current_user.idUser).order_by(Habit.habitName).all()

    if request.method == 'POST':
        if plan:
            return _plan_bloqueado()
        incluidos = [h for h in habits if request.form.get(f'incluir_{h.idHabit}')]
        if not incluidos:
            flash("Elige al menos un hábito para este mes.", "danger")
            return redirect(url_for('habits.plan_mes'))
        ids_incluidos = {h.idHabit for h in incluidos}
        for h in habits:
            if h.idHabit in ids_incluidos:
                h.habitState = 'Activo'
                h.set_dias(request.form.getlist(f'dias_{h.idHabit}'))
            else:
                h.habitState = 'Pausado'
        db.session.add(PlanMensual(idUser=current_user.idUser, anio=hoy.year, mes=hoy.month))
        try:
            db.session.commit()
        except IntegrityError:
            # Doble envío: el plan del mes ya se había guardado
            db.session.rollback()
        flash(f"Plan de {nombre_mes(hoy)} confirmado. Queda fijo hasta el próximo mes.", "success")
        return redirect(url_for('auth.dashboard'))

    return render_template(
        "register/plan_mes.html",
        habits=habits,
        plan=plan,
        mes=nombre_mes(hoy),
        desbloqueo=primer_dia_mes_siguiente(hoy),
    )

@bp.route('/register_habit', methods=['GET', 'POST'])
@login_required
def register_habit():
    if request.method == 'POST':
        bloqueo = _plan_bloqueado()
        if bloqueo:
            return bloqueo
        habit_name = request.form.get('habitName')
        habit_desc = request.form.get('habitDesc')
        habit_freq = request.form.get('habitFreq')
        habit_category = request.form.get('habitCategory')
        
        new_habit = Habit(
            idUser=current_user.idUser,
            habitName=habit_name,
            habitDesc=habit_desc,
            habitFreq=habit_freq,
            habitCategory=habit_category,
            habitState='Activo'
        )
        new_habit.set_dias(request.form.getlist('diasSemana'))
        db.session.add(new_habit)
        db.session.commit()
        
        flash(f"Hábito '{habit_name}' registrado exitosamente!", "success")
        return redirect(url_for('habits.register_habit'))
    
    habits = Habit.query.filter_by(idUser=current_user.idUser).order_by(Habit.createdAt.desc()).all()
    hoy = date.today()
    return render_template(
        "register/index.html",
        habits=habits,
        plan=PlanMensual.del_mes(current_user.idUser),
        mes=nombre_mes(hoy),
        desbloqueo=primer_dia_mes_siguiente(hoy),
    )

@bp.route('/habitos/check')
@login_required
def habits_check():
    hoy = date.today()
    habits = Habit.query.filter_by(idUser=current_user.idUser).order_by(Habit.habitName).all()
    marcados_hoy = {
        h.idHabit for h in HistHabit.query.filter_by(idUser=current_user.idUser, fecha=hoy).all()
    }
    # Solo se muestran y cuentan los hábitos que tocan hoy; los demás descansan.
    # (Si uno que descansa ya se marcó hoy, se sigue mostrando para poder desmarcarlo)
    tocan_hoy = {h.idHabit for h in habits if h.toca_el(hoy)}
    descansan_hoy = sum(1 for h in habits if h.idHabit not in tocan_hoy and h.idHabit not in marcados_hoy)
    habits = [h for h in habits if h.idHabit in tocan_hoy or h.idHabit in marcados_hoy]
    total_habitos = len(tocan_hoy)
    completados_hoy = sum(1 for h in tocan_hoy if h in marcados_hoy)
    pct_hoy = round((completados_hoy / total_habitos * 100)) if total_habitos > 0 else 0
    return render_template(
        "register/check.html",
        habits=habits,
        marcados_hoy=marcados_hoy,
        tocan_hoy=tocan_hoy,
        descansan_hoy=descansan_hoy,
        total_habitos=total_habitos,
        completados_hoy=completados_hoy,
        pct_hoy=pct_hoy,
        necesita_plan=PlanMensual.del_mes(current_user.idUser) is None,
        mes=nombre_mes(hoy),
    )

@bp.route('/habit/<int:habit_id>/json')
@login_required
def habit_detail_json(habit_id):
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    return jsonify(habit.to_dict())

@bp.route('/habit/<int:habit_id>/edit', methods=['POST'])
@login_required
def habit_edit(habit_id):
    bloqueo = _plan_bloqueado()
    if bloqueo:
        return bloqueo
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    habit.habitName = request.form.get('habitName', habit.habitName)
    habit.habitDesc = request.form.get('habitDesc', habit.habitDesc)
    habit.habitFreq = request.form.get('habitFreq', habit.habitFreq)
    habit.habitCategory = request.form.get('habitCategory', habit.habitCategory)
    habit.set_dias(request.form.getlist('diasSemana'))
    db.session.commit()
    flash(f"Hábito '{habit.habitName}' actualizado correctamente.", "success")
    return redirect(url_for('habits.register_habit'))

@bp.route('/habit/<int:habit_id>/state', methods=['POST'])
@login_required
def habit_change_state(habit_id):
    bloqueo = _plan_bloqueado()
    if bloqueo:
        return bloqueo
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    new_state = request.form.get('habitState')
    if new_state in ('Activo', 'Pausado', 'Completado'):
        habit.habitState = new_state
        db.session.commit()
        flash(f"Estado del hábito '{habit.habitName}' cambiado a '{new_state}'.", "success")
    return redirect(url_for('habits.register_habit'))

@bp.route('/habit/<int:habit_id>/toggle_today', methods=['POST'])
@login_required
def habit_toggle_today(habit_id):
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    hoy = date.today()
    entry = HistHabit.query.filter_by(idHabit=habit.idHabit, fecha=hoy).first()
    if entry:
        db.session.delete(entry)
        done = False
    else:
        db.session.add(HistHabit(idUser=current_user.idUser, idHabit=habit.idHabit, fecha=hoy))
        done = True
    try:
        db.session.commit()
    except IntegrityError:
        # Doble clic muy rápido: el registro de hoy ya existía, no se suma XP dos veces
        db.session.rollback()
        return jsonify({'success': True, 'done': True, 'duplicado': True})

    progress = registrar_toggle_habito(current_user.idUser, done)
    return jsonify({'success': True, 'done': done, 'xpTotal': progress.xpTotal})

@bp.route('/habit/<int:habit_id>/delete', methods=['POST'])
@login_required
def habit_delete(habit_id):
    bloqueo = _plan_bloqueado()
    if bloqueo:
        return bloqueo
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    name = habit.habitName
    SesionRecuperacion.query.filter_by(idHabit=habit.idHabit).delete()
    Recuperacion.query.filter_by(idHabit=habit.idHabit).delete()
    db.session.delete(habit)
    db.session.commit()
    flash(f"Hábito '{name}' eliminado permanentemente.", "success")
    return redirect(url_for('habits.register_habit'))






def _sesion_de_hoy(hoy):
    """El hábito que el usuario ya hizo hoy en su día libre (solo uno por día)."""
    return SesionRecuperacion.query.filter_by(idUser=current_user.idUser, fecha=hoy).first()


def _sesiones_libres(habit, hoy):
    """Veces de este mes que aún no se han gastado en completar un día perdido."""
    return (SesionRecuperacion.query
            .filter_by(idHabit=habit.idHabit, idRecuperacion=None)
            .filter(SesionRecuperacion.fecha >= inicio_mes(hoy))
            .order_by(SesionRecuperacion.fecha).all())


def _estado_recuperacion(habit, hoy, sesion_hoy):
    hechos = {h.fecha for h in HistHabit.query.filter_by(idHabit=habit.idHabit).all()}
    perdidos = dias_perdidos(habit, hechos, hoy)
    veces = len(_sesiones_libres(habit, hoy))
    libre = dia_libre(habit, hoy)
    # Hoy solo cuenta como día libre por usar si todavía no se sumó ningún hábito
    desde = hoy if sesion_hoy is None else hoy + timedelta(days=1)
    alcanzan = cuantos_se_pueden_recuperar(perdidos, veces, dias_libres_que_quedan(habit, desde, hoy))
    return {
        'habit': habit,
        'perdidos': perdidos,
        'veces': veces,
        'dia_libre': libre,
        'hecho_hoy': bool(sesion_hoy and sesion_hoy.idHabit == habit.idHabit),
        # Hay días perdidos y todavía da tiempo de juntar las veces antes de fin de mes
        'recuperable': alcanzan > 0,
        'alcanzan': alcanzan,
        'puede_sumar': (alcanzan > 0 and libre and sesion_hoy is None
                        and veces < VECES_PARA_RECUPERAR),
        'puede_completar': bool(perdidos) and veces >= VECES_PARA_RECUPERAR,
    }


@bp.route('/habitos/recuperar')
@login_required
def recuperar():
    hoy = date.today()
    habits = Habit.query.filter_by(idUser=current_user.idUser, habitState='Activo').order_by(Habit.habitName).all()
    sesion_hoy = _sesion_de_hoy(hoy)
    # Solo los hábitos con días que de verdad se pueden recuperar este mes
    estados = [e for e in (_estado_recuperacion(h, hoy, sesion_hoy) for h in habits) if e['recuperable']]
    recuperados = (Recuperacion.query.filter_by(idUser=current_user.idUser)
                   .filter(Recuperacion.fechaRecuperada >= inicio_mes(hoy))
                   .order_by(Recuperacion.fechaRecuperada.desc()).all())
    nombres = {h.idHabit: h.habitName for h in habits}
    return render_template("register/recuperar.html", estados=estados, recuperados=recuperados,
                           sesion_hoy=sesion_hoy, nombres=nombres, hoy=hoy,
                           veces_para_recuperar=VECES_PARA_RECUPERAR)


@bp.route('/habit/<int:habit_id>/sesion_recuperacion', methods=['POST'])
@login_required
def habit_sesion_recuperacion(habit_id):
    """Registra que hoy, día libre del hábito, se hizo igual: suma 1 de 3."""
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    hoy = date.today()
    sesion_hoy = _sesion_de_hoy(hoy)
    estado = _estado_recuperacion(habit, hoy, sesion_hoy)

    if not estado['perdidos']:
        flash(f"'{habit.habitName}' está al día: no hay nada que recuperar.", "info")
    elif not estado['dia_libre']:
        flash(f"Hoy le toca '{habit.habitName}': para recuperar, hazlo en un día que no le toque.", "warning")
    elif sesion_hoy:
        flash("Hoy ya hiciste un hábito en su día libre. Solo se puede uno por día.", "warning")
    elif not estado['recuperable']:
        flash(f"Ya no quedan suficientes días libres este mes para recuperar '{habit.habitName}'.", "warning")
    elif estado['veces'] >= VECES_PARA_RECUPERAR:
        flash(f"Ya tienes {VECES_PARA_RECUPERAR}/{VECES_PARA_RECUPERAR} de '{habit.habitName}': elige el día que quieres completar.", "info")
    else:
        db.session.add(SesionRecuperacion(idUser=current_user.idUser, idHabit=habit.idHabit, fecha=hoy))
        try:
            db.session.commit()
        except IntegrityError:
            # Doble clic: ya estaba registrado hoy
            db.session.rollback()
            return redirect(url_for('habits.recuperar'))
        veces = estado['veces'] + 1
        if veces >= VECES_PARA_RECUPERAR:
            flash(f"¡{veces}/{VECES_PARA_RECUPERAR} de '{habit.habitName}'! Ya puedes completar un día perdido.", "success")
        else:
            flash(f"{veces}/{VECES_PARA_RECUPERAR} de '{habit.habitName}'. ¡Sigue así!", "success")
    return redirect(url_for('habits.recuperar'))


@bp.route('/habit/<int:habit_id>/recuperar', methods=['POST'])
@login_required
def habit_recuperar(habit_id):
    """Con VECES_PARA_RECUPERAR veces en días libres, completa un día perdido del mes."""
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    hoy = date.today()
    estado = _estado_recuperacion(habit, hoy, _sesion_de_hoy(hoy))

    try:
        fecha_perdida = date.fromisoformat(request.form.get('fecha', ''))
    except ValueError:
        fecha_perdida = None
    if fecha_perdida not in estado['perdidos']:
        flash("Ese día no se puede recuperar.", "danger")
        return redirect(url_for('habits.recuperar'))
    if not estado['puede_completar']:
        faltan = VECES_PARA_RECUPERAR - estado['veces']
        flash(f"Te {'falta' if faltan == 1 else 'faltan'} {faltan} de '{habit.habitName}' en sus días libres "
              f"para completar un día.", "warning")
        return redirect(url_for('habits.recuperar'))

    dia_estaba_vacio = HistHabit.query.filter_by(idUser=current_user.idUser, fecha=fecha_perdida).first() is None
    recuperacion = Recuperacion(idUser=current_user.idUser, idHabit=habit.idHabit,
                                fechaPerdida=fecha_perdida, fechaRecuperada=hoy)
    db.session.add(recuperacion)
    db.session.add(HistHabit(idUser=current_user.idUser, idHabit=habit.idHabit, fecha=fecha_perdida))
    try:
        db.session.flush()
    except IntegrityError:
        # Doble clic: ese día ya se había completado
        db.session.rollback()
        return redirect(url_for('habits.recuperar'))
    for sesion in _sesiones_libres(habit, hoy)[:VECES_PARA_RECUPERAR]:
        sesion.idRecuperacion = recuperacion.idRecuperacion

    registrar_recuperacion(current_user.idUser, fecha_perdida, dia_estaba_vacio)
    flash(f"¡Completaste '{habit.habitName}' del {fecha_perdida.strftime('%d/%m')}! +XP", "success")
    return redirect(url_for('habits.recuperar'))
