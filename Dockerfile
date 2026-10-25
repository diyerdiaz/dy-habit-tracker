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

# Respaldo continuo: Litestream (base de datos) y rclone (archivos subidos).
# Ver litestream.yml y docker-entrypoint.sh; sin RESPALDO_BUCKET no se usan.
# El binario de Litestream se verifica con su checksum oficial antes de instalarlo.
ARG LITESTREAM_VERSION=0.5.17
RUN apt-get update \
    && apt-get install -y --no-install-recommends rclone ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && case "$(dpkg --print-architecture)" in \
         amd64) ARQ=x86_64; SHA=cfb371176d164437ae869f8351cfde49bd1804ae71c61923f75c9cba9c9c006d ;; \
         arm64) ARQ=arm64;  SHA=f8ca4a050095c1efbda2c4365172e61bf9d955ea0d9ac42f448b52e51819baa5 ;; \
         *) echo "Arquitectura sin Litestream" >&2; exit 1 ;; \
       esac \
    && python -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], '/tmp/litestream.tar.gz')" \
         "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-${ARQ}.tar.gz" \
    && echo "$SHA  /tmp/litestream.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin litestream \
    && rm /tmp/litestream.tar.gz \
    && litestream version

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
