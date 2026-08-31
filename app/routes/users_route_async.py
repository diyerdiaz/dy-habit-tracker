from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from app.models.users import User
from app import db
from io import BytesIO
import base64
import json

bp = Blueprint('userAsync', __name__, url_prefix='/UserAsync')

@bp.route('/index', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@bp.route('/add', methods=['POST'])
def create_user():
    print("entra a create")
    data = request.json
    new_user = User(nameUser=data['nameUser'], passwordUser=data['passwordUser'])
    new_user.save()
    return jsonify({'message': 'User created successfully'}), 201

@bp.route('/update/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get(id)
    if user:
        data = request.json
        user.nameUser = data['nameUser']
        user.passwordUser = data['passwordUser']
        db.session.commit()
        # Notifica a todos los clientes conectados sobre la actualización
        return jsonify({'message': 'User updated successfully'})
    return jsonify({'message': 'User not found'}), 404

@bp.route('/delete/<int:id>', methods=['DELETE'])
def delete_user(id):
    print("entra de delete")
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})
    return jsonify({'message': 'User not found'}), 404