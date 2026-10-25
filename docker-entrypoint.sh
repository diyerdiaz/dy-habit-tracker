#!/bin/sh
# Arranque del contenedor.
# Coolify (y Docker) crean la carpeta del volumen instance/ con dueño root, y la
# app corre con un usuario sin privilegios que no podría escribir ahí la base de
# datos ni la clave secreta. Por eso se entra como root solo para darle esa
# carpeta a "appuser", y luego este mismo script sigue como appuser.
set -e

APP_DIR="${APP_DIR:-/app}"
INSTANCE="$APP_DIR/instance"
DB="$INSTANCE/flaskdb.sqlite"
CONFIG="$APP_DIR/litestream.yml"
# Cada cuánto se copian a la nube los archivos subidos (fotos, apuntes)
RESPALDO_INTERVALO_ARCHIVOS="${RESPALDO_INTERVALO_ARCHIVOS:-3600}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$INSTANCE"
    chown -R appuser:appuser "$INSTANCE"
    # setpriv no cambia HOME: sin esto rclone busca su configuración en /root
    export HOME=/home/appuser
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$0" "$@"
fi

# Sin bucket configurado no hay respaldo: la app arranca igual que siempre
if [ -z "$RESPALDO_BUCKET" ]; then
    exec "$@"
fi

# R2 usa la región "auto"; Backblaze u otros pueden necesitar otra
export RESPALDO_REGION="${RESPALDO_REGION:-auto}"

# rclone (archivos subidos) se configura con las mismas llaves, sin archivo de config
export RCLONE_CONFIG_RESPALDO_TYPE=s3
export RCLONE_CONFIG_RESPALDO_PROVIDER="${RESPALDO_PROVEEDOR:-Cloudflare}"
export RCLONE_CONFIG_RESPALDO_ENDPOINT="$RESPALDO_ENDPOINT"
export RCLONE_CONFIG_RESPALDO_REGION="$RESPALDO_REGION"
export RCLONE_CONFIG_RESPALDO_ACCESS_KEY_ID="$RESPALDO_ACCESS_KEY_ID"
export RCLONE_CONFIG_RESPALDO_SECRET_ACCESS_KEY="$RESPALDO_SECRET_ACCESS_KEY"
export RCLONE_CONFIG_RESPALDO_NO_CHECK_BUCKET=true
REMOTO="respaldo:$RESPALDO_BUCKET/instance"
# La base de datos la respalda Litestream; rclone solo copia lo demás
# (subidas y clave secreta), nunca el .sqlite ni los archivos de trabajo de Litestream.
rclone_archivos() {
    rclone "$@" --exclude '*.sqlite*' --exclude '.*-litestream/**'
}

# Servidor nuevo (sin base de datos): se recupera todo desde el respaldo
if [ ! -f "$DB" ]; then
    echo "[respaldo] No hay base de datos local: restaurando desde el bucket..."
    rclone_archivos copy "$REMOTO" "$INSTANCE" || echo "[respaldo] No se pudieron restaurar los archivos subidos"
    litestream restore -config "$CONFIG" -if-db-not-exists -if-replica-exists "$DB"
fi

# Copia periódica de los archivos subidos (en segundo plano)
(
    while true; do
        rclone_archivos sync "$INSTANCE" "$REMOTO" || echo "[respaldo] Falló la copia de archivos subidos"
        sleep "$RESPALDO_INTERVALO_ARCHIVOS"
    done
) &

# Litestream vigila la base de datos y arranca la app; si la app termina, termina él
exec litestream replicate -config "$CONFIG" -exec "$*"
