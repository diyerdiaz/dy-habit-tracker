"""Respaldo continuo (Litestream + rclone): docker-entrypoint.sh, litestream.yml,
Dockerfile y docker-compose.yml. El arranque se prueba con litestream y rclone
falsos que solo anotan cómo los llamaron."""
import os
import re
import signal
import subprocess
import textwrap
from pathlib import Path

import pytest

from config import Config

RAIZ = Path(__file__).resolve().parent.parent.parent
ENTRYPOINT = RAIZ / "docker-entrypoint.sh"
LITESTREAM_YML = RAIZ / "litestream.yml"
VARIABLES = ("RESPALDO_BUCKET", "RESPALDO_ENDPOINT",
             "RESPALDO_ACCESS_KEY_ID", "RESPALDO_SECRET_ACCESS_KEY")

pytestmark = pytest.mark.skipif(os.geteuid() == 0, reason="el arranque como root cambia de usuario")


@pytest.fixture
def entorno(tmp_path):
    """Carpeta de la app falsa, binarios falsos y un log de lo que se ejecutó."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "llamadas.log"
    (bin_dir / "rclone").write_text(textwrap.dedent(f"""\
        #!/bin/sh
        echo "rclone $*" >> {log}
        """))
    # Al arrancar la app (replicate) espera a que corra la primera copia de archivos
    (bin_dir / "litestream").write_text(textwrap.dedent(f"""\
        #!/bin/sh
        echo "litestream $*" >> {log}
        if [ "$1" = replicate ]; then
            i=0
            while [ $i -lt 50 ] && ! grep -q "rclone sync" {log}; do sleep 0.1; i=$((i+1)); done
        fi
        """))
    for binario in bin_dir.iterdir():
        binario.chmod(0o755)
    app_dir = tmp_path / "app"
    (app_dir / "instance").mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("RESPALDO_")}
    env.update(PATH=f"{bin_dir}:{env['PATH']}", APP_DIR=str(app_dir),
               RESPALDO_INTERVALO_ARCHIVOS="60")
    return env, app_dir, log


def _arrancar(env, *comando):
    # La salida va a un archivo: el ciclo de copia en segundo plano la dejaría
    # abierta y un pipe nunca terminaría de leerse
    salida = Path(env["APP_DIR"]).parent / "salida.txt"
    with open(salida, "w") as destino:
        proceso = subprocess.Popen(["sh", str(ENTRYPOINT), *comando], env=env,
                                   stdout=destino, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            proceso.wait(timeout=15)
        finally:
            # El ciclo de copia de archivos queda en segundo plano: se apaga aquí
            try:
                os.killpg(proceso.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    return proceso.returncode, salida.read_text()


def _con_respaldo(env):
    return {**env, "RESPALDO_BUCKET": "mi-bucket", "RESPALDO_ENDPOINT": "https://x.r2.cloudflarestorage.com",
            "RESPALDO_ACCESS_KEY_ID": "id", "RESPALDO_SECRET_ACCESS_KEY": "secreto"}


def test_sin_bucket_arranca_la_app_sin_respaldo(entorno):
    env, _, log = entorno
    codigo, salida = _arrancar(env, "echo", "app-arrancada")
    assert codigo == 0
    assert "app-arrancada" in salida
    assert not log.exists()  # ni litestream ni rclone


def test_con_bucket_y_base_existente_replica_sin_restaurar(entorno):
    env, app_dir, log = entorno
    (app_dir / "instance" / "flaskdb.sqlite").write_bytes(b"")
    codigo, _ = _arrancar(_con_respaldo(env), "gunicorn", "run:app", "--workers", "2")
    assert codigo == 0
    llamadas = log.read_text()
    assert "restore" not in llamadas
    assert "rclone copy" not in llamadas
    assert f"litestream replicate -config {app_dir}/litestream.yml -exec gunicorn run:app --workers 2" in llamadas
    sync = next(l for l in llamadas.splitlines() if l.startswith("rclone sync"))
    assert f"{app_dir}/instance respaldo:mi-bucket/instance" in sync
    # La base de datos nunca la copia rclone (es trabajo de Litestream)
    assert "--exclude *.sqlite*" in sync
    assert "--exclude .*-litestream/**" in sync


def test_servidor_nuevo_restaura_antes_de_arrancar(entorno):
    env, app_dir, log = entorno
    codigo, _ = _arrancar(_con_respaldo(env), "gunicorn", "run:app")
    assert codigo == 0
    llamadas = log.read_text().splitlines()
    db = f"{app_dir}/instance/flaskdb.sqlite"
    restore = next(i for i, l in enumerate(llamadas) if l.startswith("litestream restore"))
    copy = next(i for i, l in enumerate(llamadas) if l.startswith("rclone copy"))
    replicate = next(i for i, l in enumerate(llamadas) if l.startswith("litestream replicate"))
    assert copy < replicate and restore < replicate
    assert llamadas[restore].endswith(f"-if-db-not-exists -if-replica-exists {db}")
    assert llamadas[copy].startswith(f"rclone copy respaldo:mi-bucket/instance {app_dir}/instance")


def test_rclone_usa_las_mismas_llaves(entorno, tmp_path):
    env, app_dir, _ = entorno
    (app_dir / "instance" / "flaskdb.sqlite").write_bytes(b"")
    volcado = tmp_path / "entorno.txt"
    (Path(env["PATH"].split(":")[0]) / "rclone").write_text(
        f"#!/bin/sh\nenv | grep RCLONE_CONFIG_RESPALDO > {volcado}\necho \"rclone $*\" >> {tmp_path}/llamadas.log\n")
    _arrancar(_con_respaldo(env), "true")
    variables = dict(l.split("=", 1) for l in volcado.read_text().splitlines())
    assert variables["RCLONE_CONFIG_RESPALDO_TYPE"] == "s3"
    assert variables["RCLONE_CONFIG_RESPALDO_ENDPOINT"] == "https://x.r2.cloudflarestorage.com"
    assert variables["RCLONE_CONFIG_RESPALDO_ACCESS_KEY_ID"] == "id"
    assert variables["RCLONE_CONFIG_RESPALDO_SECRET_ACCESS_KEY"] == "secreto"
    assert variables["RCLONE_CONFIG_RESPALDO_REGION"] == "auto"


def test_litestream_respalda_la_base_de_la_app():
    # La app usa sqlite:///flaskdb.sqlite, que Flask-SQLAlchemy guarda en instance/,
    # y en el contenedor el proyecto vive en /app (WORKDIR del Dockerfile)
    assert Config.SQLALCHEMY_DATABASE_URI == "sqlite:///flaskdb.sqlite" or "DATABASE_URL" in os.environ
    assert "WORKDIR /app" in (RAIZ / "Dockerfile").read_text()
    assert "path: /app/instance/flaskdb.sqlite" in LITESTREAM_YML.read_text()


def test_litestream_yml_sin_llaves_reales():
    texto = LITESTREAM_YML.read_text()
    for clave in ("bucket", "endpoint", "access-key-id", "secret-access-key"):
        valor = re.search(rf"^\s+{clave}:\s*(.+)$", texto, re.M).group(1).strip()
        assert re.fullmatch(r"\$\{RESPALDO_[A-Z_]+\}", valor), f"{clave} debe venir de una variable"


def test_compose_pasa_las_variables_del_respaldo():
    # Con Docker Compose, Coolify solo entrega las variables nombradas en el compose
    compose = (RAIZ / "docker-compose.yml").read_text()
    for variable in VARIABLES:
        assert f"{variable}: ${{{variable}:-}}" in compose, variable


def test_dockerfile_instala_litestream_verificado():
    dockerfile = (RAIZ / "Dockerfile").read_text()
    assert re.search(r"ARG LITESTREAM_VERSION=\d+\.\d+\.\d+", dockerfile)
    assert "sha256sum -c" in dockerfile
    assert "rclone" in dockerfile
    assert "litestream.yml" not in (RAIZ / ".dockerignore").read_text()


def test_al_bajar_a_appuser_cambia_home():
    # Como root el script se vuelve a ejecutar como appuser; HOME debe ser el suyo
    # (si queda /root, rclone falla con "permission denied" al buscar su config)
    texto = ENTRYPOINT.read_text()
    inicio = texto.index('if [ "$(id -u)" = "0" ]')
    bloque_root = texto[inicio:texto.index("\nfi\n", inicio)]
    assert "export HOME=/home/appuser" in bloque_root
    assert bloque_root.index("export HOME") < bloque_root.index("exec setpriv")
