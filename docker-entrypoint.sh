#!/bin/sh
# Arranque del contenedor.
# Coolify (y Docker) crean la carpeta del volumen instance/ con dueño root, y la
# app corre con un usuario sin privilegios que no podría escribir ahí la base de
# datos ni la clave secreta. Por eso se entra como root solo para darle esa
# carpeta a "appuser", y luego se cede el control a gunicorn como appuser.
set -e

if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/instance
    chown -R appuser:appuser /app/instance
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi

exec "$@"
