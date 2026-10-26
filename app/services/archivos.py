"""Archivos subidos por los usuarios (apuntes y fotos de perfil) dentro de UPLOAD_FOLDER."""
import os
from flask import current_app


def carpeta_apuntes(idUser):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'apuntes', str(idUser))


def borrar_apuntes(apuntes):
    """Borra del disco los archivos de una lista de apuntes (los registros los
    borra la base de datos en cascada)."""
    for apunte in apuntes:
        ruta = os.path.join(carpeta_apuntes(apunte.idUser), apunte.nombreGuardado)
        try:
            os.remove(ruta)
        except FileNotFoundError:
            pass


def carpeta_avatars():
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')


def borrar_foto(user):
    if user.avatar:
        try:
            os.remove(os.path.join(carpeta_avatars(), user.avatar))
        except FileNotFoundError:
            pass
        user.avatar = None


def borrar_imagenes_vision(idUser, nombres):
    """Borra del disco las imágenes indicadas del vision board del usuario (solo
    esos archivos) y la carpeta si queda vacía. Nunca borra la carpeta con todo."""
    carpeta = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vision', str(idUser))
    for nombre in nombres:
        try:
            os.remove(os.path.join(carpeta, os.path.basename(nombre)))
        except FileNotFoundError:
            pass
    try:
        os.rmdir(carpeta)   # solo funciona si está vacía
    except OSError:
        pass
