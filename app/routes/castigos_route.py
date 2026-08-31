from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models.ruleta_castigo import Castigo
from app import db

bp = Blueprint('castigos', __name__)

@bp.route('/castigos', methods=['GET', 'POST'])
@login_required
def castigos_index():
    if request.method == 'POST':
        castigo_name = request.form.get('castigoName')
        castigo_desc = request.form.get('castigoDesc')
        castigo_category = request.form.get('castigoCategory')
        
        new_castigo = Castigo(
            idUser=current_user.idUser,
            castigoName=castigo_name,
            castigoDesc=castigo_desc,
            castigoCategory=castigo_category,
            castigoState='Pendiente'
        )
        db.session.add(new_castigo)
        db.session.commit()
        
        flash(f"Castigo '{castigo_name}' registrado exitosamente!", "success")
        return redirect(url_for('castigos.castigos_index'))
    
    castigos = Castigo.query.filter_by(idUser=current_user.idUser).order_by(Castigo.createdAt.desc()).all()
    return render_template("castigos/index.html", castigos=castigos)

@bp.route('/castigo/<int:castigo_id>/json')
@login_required
def castigo_detail_json(castigo_id):
    castigo = Castigo.query.filter_by(idCastigo=castigo_id, idUser=current_user.idUser).first_or_404()
    return jsonify(castigo.to_dict())

@bp.route('/castigo/<int:castigo_id>/edit', methods=['POST'])
@login_required
def castigo_edit(castigo_id):
    castigo = Castigo.query.filter_by(idCastigo=castigo_id, idUser=current_user.idUser).first_or_404()
    castigo.castigoName = request.form.get('castigoName', castigo.castigoName)
    castigo.castigoDesc = request.form.get('castigoDesc', castigo.castigoDesc)
    castigo.castigoCategory = request.form.get('castigoCategory', castigo.castigoCategory)
    db.session.commit()
    flash(f"Castigo '{castigo.castigoName}' actualizado correctamente.", "success")
    return redirect(url_for('castigos.castigos_index'))

@bp.route('/castigo/<int:castigo_id>/state', methods=['POST'])
@login_required
def castigo_change_state(castigo_id):
    castigo = Castigo.query.filter_by(idCastigo=castigo_id, idUser=current_user.idUser).first_or_404()
    new_state = request.form.get('castigoState')
    if new_state in ('Pendiente', 'En progreso', 'Completado'):
        castigo.castigoState = new_state
        db.session.commit()
        flash(f"Estado del castigo '{castigo.castigoName}' cambiado a '{new_state}'.", "success")
    return redirect(url_for('castigos.castigos_index'))

@bp.route('/castigo/<int:castigo_id>/delete', methods=['POST'])
@login_required
def castigo_delete(castigo_id):
    castigo = Castigo.query.filter_by(idCastigo=castigo_id, idUser=current_user.idUser).first_or_404()
    name = castigo.castigoName
    db.session.delete(castigo)
    db.session.commit()
    flash(f"Castigo '{name}' eliminado permanentemente.", "success")
    return redirect(url_for('castigos.castigos_index'))
