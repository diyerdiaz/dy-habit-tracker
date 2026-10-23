"""Configuración del correo (SMTP): lectura del .env y que el secreto no se versione."""
import importlib
from pathlib import Path

import pytest

import config

RAIZ = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def _restaurar_config():
    # Autouse: se desmonta después de monkeypatch, con el entorno ya restaurado,
    # para que la Config recargada en un test no se filtre a los demás
    yield
    importlib.reload(config)


def _recargar_config(monkeypatch, **variables):
    # Las credenciales quedan definidas (vacías o con el valor del test) ANTES de
    # recargar: _cargar_env no pisa variables existentes, así el .env real no influye
    monkeypatch.delenv("MAIL_SERVER", raising=False)
    monkeypatch.delenv("MAIL_PORT", raising=False)
    for clave in ("MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM"):
        monkeypatch.setenv(clave, variables.pop(clave, ""))
    return importlib.reload(config).Config


def test_cargar_env_lee_claves_e_ignora_comentarios(tmp_path, monkeypatch):
    monkeypatch.delenv("PRUEBA_A", raising=False)
    monkeypatch.delenv("PRUEBA_B", raising=False)
    env = tmp_path / ".env"
    env.write_text('# comentario\n\nPRUEBA_A=hola\nPRUEBA_B="con comillas"\nlinea sin igual\n')
    config._cargar_env(str(env))
    import os
    assert os.environ["PRUEBA_A"] == "hola"
    assert os.environ["PRUEBA_B"] == "con comillas"


def test_cargar_env_no_pisa_variables_existentes(tmp_path, monkeypatch):
    monkeypatch.setenv("PRUEBA_C", "del_servidor")
    env = tmp_path / ".env"
    env.write_text("PRUEBA_C=del_archivo\n")
    config._cargar_env(str(env))
    import os
    assert os.environ["PRUEBA_C"] == "del_servidor"


def test_cargar_env_sin_archivo_no_falla(tmp_path):
    config._cargar_env(str(tmp_path / "no_existe.env"))


def test_correo_apagado_sin_credenciales(monkeypatch):
    cfg = _recargar_config(monkeypatch)
    assert cfg.MAIL_ENABLED is False
    assert cfg.MAIL_SERVER == "smtp.gmail.com"
    assert cfg.MAIL_PORT == 587


def test_correo_activo_con_credenciales_y_clave_sin_espacios(monkeypatch):
    cfg = _recargar_config(
        monkeypatch, MAIL_USERNAME="app@gmail.com", MAIL_PASSWORD="abcd efgh ijkl mnop"
    )
    assert cfg.MAIL_ENABLED is True
    assert cfg.MAIL_PASSWORD == "abcdefghijklmnop"
    # Sin MAIL_FROM, el remitente es la misma cuenta
    assert cfg.MAIL_FROM == "app@gmail.com"


def test_env_no_se_sube_a_git_ni_a_docker():
    gitignore = (RAIZ / ".gitignore").read_text().splitlines()
    dockerignore = (RAIZ / ".dockerignore").read_text().splitlines()
    assert ".env" in gitignore
    assert ".env" in dockerignore


def test_env_example_no_tiene_secretos_reales():
    ejemplo = (RAIZ / ".env.example").read_text()
    assert "MAIL_PASSWORD=tu_clave_de_16_letras" in ejemplo


def test_tests_no_usan_correo_real(app):
    assert app.config["MAIL_ENABLED"] is False


def test_docker_compose_pasa_las_variables_del_correo_sin_valores():
    # Con Docker Compose (Coolify) solo llegan al contenedor las variables nombradas
    # en el compose; los valores reales van en Coolify, nunca en el archivo
    compose = (RAIZ / "docker-compose.yml").read_text()
    assert "MAIL_USERNAME: ${MAIL_USERNAME:-}" in compose
    assert "MAIL_PASSWORD: ${MAIL_PASSWORD:-}" in compose
    assert "APP_URL: ${SERVICE_URL_APP:-}" in compose
