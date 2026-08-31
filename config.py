import os
import secrets

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///flaskdb.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = secrets.token_urlsafe(24)

#Comandos para descargar en instalar todas las librerias offline  
#python -m pip download -r requirements.txt -d librerias
#pip install --no-index --find-links=librerias -r requirements.txt