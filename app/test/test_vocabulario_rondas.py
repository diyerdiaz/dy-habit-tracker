"""Vocabulario: las palabras marcadas "Difícil" salen primero en la siguiente
ronda, y ninguna palabra se repite dentro de una ronda. Se prueba el mismo JS
de la página (static/js/vocabulario.js) corriéndolo con node."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import db
from app.models.vocabulario import Vocabulario

JS = Path(__file__).resolve().parents[1] / 'static' / 'js' / 'vocabulario.js'

# El JS busca elementos de la página al cargar: en node se le da un document vacío
_DOCUMENT_FALSO = """
global.document = {
    getElementById: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {},
};
"""


def _rondas(palabras, cantidad, veces=300):
    """Arma `veces` rondas con el JS real y devuelve los nombres de cada una."""
    if not shutil.which('node'):
        pytest.skip('node no está instalado')
    codigo = _DOCUMENT_FALSO + f"""
const {{ vocabSeleccionPonderada }} = require({json.dumps(str(JS))});
const palabras = {json.dumps(palabras)};
const rondas = [];
for (let i = 0; i < {veces}; i++) {{
    rondas.push(vocabSeleccionPonderada(palabras, {cantidad}).map((p) => p.nombre));
}}
console.log(JSON.stringify(rondas));
"""
    salida = subprocess.run(['node', '-e', codigo], capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


def _palabra(nombre, calificacion=None, veces=0):
    peso = {'dificil': 3, 'medio': 2, 'facil': 1}.get(calificacion, 2)
    return {'nombre': nombre, 'ultimaCalificacion': calificacion, 'vecesMostrada': veces, 'peso': peso}


def test_las_dificiles_salen_primero_aunque_hayan_salido_mas_veces():
    palabras = [
        _palabra('Habit', 'dificil', veces=4),
        _palabra('Schedule', 'dificil', veces=3),
        _palabra('Effort', 'dificil', veces=1),
        _palabra('Goal', 'facil', veces=1),
        _palabra('Reliable', 'facil', veces=1),
        _palabra('Overcome', 'facil', veces=2),
        _palabra('Achieve', 'medio', veces=4),
    ]
    for ronda in _rondas(palabras, 5):
        assert set(ronda[:3]) == {'Habit', 'Schedule', 'Effort'}
        # El resto se completa por turnos: primero las que menos han salido
        assert set(ronda[3:]) == {'Goal', 'Reliable'}


def test_ninguna_palabra_se_repite_en_la_ronda():
    palabras = [_palabra(f'P{i}', ('dificil', 'medio', 'facil', None)[i % 4], veces=i % 3) for i in range(12)]
    for cantidad in (1, 5, 12, 20):
        for ronda in _rondas(palabras, cantidad, veces=100):
            assert len(ronda) == len(set(ronda)) == min(cantidad, 12)


def test_si_hay_mas_dificiles_que_la_ronda_van_las_que_menos_han_salido():
    palabras = [
        _palabra('D1', 'dificil', veces=5),
        _palabra('D2', 'dificil', veces=1),
        _palabra('D3', 'dificil', veces=1),
        _palabra('F1', 'facil', veces=0),
    ]
    for ronda in _rondas(palabras, 2):
        assert set(ronda) == {'D2', 'D3'}


def test_al_marcarla_mas_facil_vuelve_al_turno_normal():
    palabras = [
        _palabra('Habit', 'medio', veces=4),  # antes difícil, ahora "Medio fácil"
        _palabra('Goal', 'facil', veces=1),
        _palabra('Effort', None, veces=1),
    ]
    for ronda in _rondas(palabras, 2):
        assert set(ronda) == {'Goal', 'Effort'}


def test_sin_dificiles_funciona_como_antes():
    palabras = [_palabra('A', 'facil', veces=2), _palabra('B', 'medio', veces=0), _palabra('C', None, veces=0)]
    for ronda in _rondas(palabras, 2):
        assert set(ronda) == {'B', 'C'}


# ── De punta a punta: calificar en una ronda cambia la siguiente ──

def _palabras_de_la_pagina(logged_client):
    html = logged_client.get('/menu/ingles/vocabulario/aprender').get_data(as_text=True)
    return json.loads(re.search(r'window\.VOCAB_PALABRAS = (.*?);\n', html).group(1))


def test_la_pagina_envia_la_ultima_calificacion(logged_client, user):
    palabra = Vocabulario(idUser=user.idUser, nombre='Habit', significado='Hábito')
    db.session.add(palabra)
    db.session.commit()
    assert _palabras_de_la_pagina(logged_client)[0]['ultimaCalificacion'] is None
    for cal in ('facil', 'dificil'):
        logged_client.post('/menu/ingles/vocabulario/calificar',
                           json={'idVocab': palabra.idVocab, 'nombre': 'Habit', 'calificacion': cal})
    datos = _palabras_de_la_pagina(logged_client)[0]
    assert datos['ultimaCalificacion'] == 'dificil' and datos['vecesMostrada'] == 2


def test_las_3_dificiles_de_la_ronda_anterior_salen_primero(logged_client, user):
    nombres = ['Habit', 'Goal', 'Effort', 'Achieve', 'Improve', 'Schedule', 'Reliable', 'Overcome']
    palabras = {}
    for n in nombres:
        palabras[n] = Vocabulario(idUser=user.idUser, nombre=n, significado=n.lower())
        db.session.add(palabras[n])
    db.session.commit()

    # Ronda anterior: 5 palabras, 3 marcadas difíciles
    calificaciones = {'Habit': 'dificil', 'Goal': 'facil', 'Effort': 'dificil', 'Achieve': 'medio', 'Improve': 'dificil'}
    for n, cal in calificaciones.items():
        logged_client.post('/menu/ingles/vocabulario/calificar',
                           json={'idVocab': palabras[n].idVocab, 'nombre': n, 'calificacion': cal})

    for ronda in _rondas(_palabras_de_la_pagina(logged_client), 5):
        assert set(ronda[:3]) == {'Habit', 'Effort', 'Improve'}
        # Luego las que no salieron en la ronda anterior
        assert set(ronda[3:]) <= {'Schedule', 'Reliable', 'Overcome'}
        assert len(set(ronda)) == 5
