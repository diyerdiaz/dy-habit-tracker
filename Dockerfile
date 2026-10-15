# Imagen de producción de la app (Flask + gunicorn) en el puerto 4000.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Primero solo las dependencias: así Docker reutiliza esta capa si cambia el código
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Usuario sin privilegios (uid 1000, el mismo del usuario normal en Linux, para
# poder montar la carpeta instance/ del equipo sin problemas de permisos).
# instance/ guarda la base de datos, la clave secreta y los archivos subidos.
RUN useradd --uid 1000 --create-home appuser \
    && mkdir -p /app/instance \
    && chown -R appuser:appuser /app/instance
USER appuser

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/', timeout=4)" || exit 1

# --preload: crea/actualiza las tablas una sola vez antes de arrancar los workers
CMD ["gunicorn", "run:app", \
     "--bind", "0.0.0.0:4000", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "60", \
     "--preload", \
     "--access-logfile", "-"]
