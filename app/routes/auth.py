from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.users import User
from app.models.habitos import Habit
from app import db

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
    return render_template("dashboard.html")


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