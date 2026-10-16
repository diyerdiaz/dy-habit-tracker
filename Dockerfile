# Imagen de producción de la app (Flask + gunicorn) en el puerto 4000.
FROM python:3.12-slim

# Zona horaria de la app: el "día" (check diario, rachas, XP, frase del día)
# cambia a medianoche de esta zona. Sin esto el contenedor usa UTC (5 h antes).
ENV TZ=America/Bogota \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Primero solo las dependencias: así Docker reutiliza esta capa si cambia el código
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Usuario sin privilegios para la app (uid 1000, el mismo del usuario normal en Linux).
# instance/ guarda la base de datos, la clave secreta y los archivos subidos.
# El contenedor arranca como root solo para que docker-entrypoint.sh le dé esa
# carpeta a appuser (Coolify la crea con dueño root); gunicorn corre como appuser.
RUN useradd --uid 1000 --create-home appuser \
    && mkdir -p /app/instance \
    && chown -R appuser:appuser /app/instance \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/', timeout=4)" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# --preload: crea/actualiza las tablas una sola vez antes de arrancar los workers
CMD ["gunicorn", "run:app", \
     "--bind", "0.0.0.0:4000", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "60", \
     "--preload", \
     "--access-logfile", "-"]
