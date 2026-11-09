"""Evita volver a fijar versiones con vulnerabilidades conocidas (alertas de Dependabot)."""
from pathlib import Path

import pytest

REQUIREMENTS = Path(__file__).resolve().parents[2] / "requirements.txt"

# Versión mínima sin vulnerabilidades conocidas para cada paquete.
VERSIONES_MINIMAS = {
    "pillow": (13, 0, 0),
    "flask": (3, 1, 3),
    "jinja2": (3, 1, 6),
    "werkzeug": (3, 1, 9),
}


def _versiones_fijadas():
    fijadas = {}
    for linea in REQUIREMENTS.read_text().splitlines():
        linea = linea.split("#")[0].strip()
        if "==" in linea:
            nombre, version = linea.split("==")
            fijadas[nombre.strip().lower()] = tuple(int(p) for p in version.strip().split("."))
    return fijadas


@pytest.mark.parametrize("paquete,minima", VERSIONES_MINIMAS.items())
def test_dependencia_sin_vulnerabilidades_conocidas(paquete, minima):
    fijadas = _versiones_fijadas()
    assert paquete in fijadas, f"{paquete} no está en requirements.txt"
    assert fijadas[paquete] >= minima, (
        f"{paquete} {fijadas[paquete]} tiene vulnerabilidades conocidas; usar >= {minima}"
    )
