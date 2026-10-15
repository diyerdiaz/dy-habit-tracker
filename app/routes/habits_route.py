from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models.habitos import Habit
from app.models.hist_habits import HistHabit
from app import db
from app.gamificacion import registrar_toggle_habito
from datetime import date
from sqlalchemy.exc import IntegrityError

bp = Blueprint('habits', __name__)

@bp.route('/register_habit', methods=['GET', 'POST'])
@login_required
def register_habit():
    if request.method == 'POST':
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
    return render_template("register/index.html", habits=habits)

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
    )

@bp.route('/habit/<int:habit_id>/json')
@login_required
def habit_detail_json(habit_id):
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    return jsonify(habit.to_dict())

@bp.route('/habit/<int:habit_id>/edit', methods=['POST'])
@login_required
def habit_edit(habit_id):
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
    habit = Habit.query.filter_by(idHabit=habit_id, idUser=current_user.idUser).first_or_404()
    name = habit.habitName
    db.session.delete(habit)
    db.session.commit()
    flash(f"Hábito '{name}' eliminado permanentemente.", "success")
    return redirect(url_for('habits.register_habit'))
