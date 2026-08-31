from flask_login import UserMixin
from app import db
import qrcode
from io import BytesIO
import base64
from PIL import Image
import os
from flask import url_for, current_app

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    idUser = db.Column(db.Integer, primary_key=True)
    nameUser = db.Column(db.String(80), unique=True, nullable=False)
    passwordUser = db.Column(db.String(120), nullable=False)

    def get_id(self):
        return str(self.idUser)

    def to_dict(self):
        return {
            "idUser": self.idUser,
            "nameUser": self.nameUser,
            "pass": self.passwordUser
        }
    
    def save(self):
        db.add(self)
        db.commit()

    def generate_qr(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f'{{"ID": {self.idUser}, "Name": "{self.nameUser}"}}')
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')


    