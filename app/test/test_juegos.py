"""Juegos de vocabulario: Unir parejas."""
import json
import re
from app import db
from app.models.juego_partida import JuegoPartida
from app.models.user_progress import UserProgress
from app.models.vocabulario import Vocabulario

PALABRAS = [('give', 'dar'), ('take', 'tomar'), ('run', 'correr'), ('eat', 'comer'),
            ('sleep', 'dormir'), ('read', 'leer'), ('write', 'escribir')]


def _vocabulario(user, cuantas=len(PALABRAS)):
    for en, es in PALABRAS[:cuantas]:
        db.session.add(Vocabulario(idUser=user.idUser, nombre=en, significado=es))
    db.session.commit()
    return Vocabulario.query.filter_by(idUser=user.idUser).all()


def _sin_tokens(html):
    """Quita los tokens CSRF: son texto al azar y podrían contener 'XP' o cualquier palabra."""
    return re.sub(r'(name="csrf_token" value|name="csrf-token" content)="[^"]*"', '', html)


def _palabras_de_la_pagina(html):
    bloque = re.search(r'<script type="application/json" id="unirPalabras">(.*?)</script>', html, re.S)
    return json.loads(bloque.group(1))


def _enviar(client, ids, errores=0, segundos=30):
    return client.post('/menu/ingles/juegos/unir/resultado', json={'ids': ids, 'errores': errores, 'segundos': segundos})


def _xp(user):
    progreso = db.session.get(UserProgress, user.idUser)
    return progreso.xpTotal if progreso else 0


# ── Páginas ──

def test_juegos_requiere_login(client):
    assert client.get('/menu/ingles/juegos/').status_code == 302
    assert client.get('/menu/ingles/juegos/unir').status_code == 302
    assert _enviar(client, [1, 2, 3, 4]).status_code in (302, 401)


def test_tarjeta_juegos_en_la_pagina_de_ingles(logged_client):
    html = logged_client.get('/menu/ingles').get_data(as_text=True)
    assert '/menu/ingles/juegos/' in html and 'Juegos' in html
    assert 'id="sidebar"' in html  # el menú lateral sigue apareciendo tras pasarlo a un partial


def test_sin_palabras_suficientes_pide_agregar(logged_client, user):
    _vocabulario(user, cuantas=3)
    html = logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True)
    assert 'Necesitas al menos' in html and 'id="juegoUnir"' not in html
    menu = logged_client.get('/menu/ingles/juegos/').get_data(as_text=True)
    assert 'bloqueado' in menu


def test_la_pagina_trae_las_palabras_del_usuario(logged_client, user, other_user):
    _vocabulario(user)
    db.session.add(Vocabulario(idUser=other_user.idUser, nombre='secret', significado='secreto'))
    db.session.commit()
    html = logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True)
    assert 'id="juegoUnir"' in html and 'js/juegos.js' in html and 'css/juegos.css' in html
    datos = _palabras_de_la_pagina(html)
    assert {p['en'] for p in datos} == {en for en, _ in PALABRAS}
    assert 'secret' not in _sin_tokens(html)  # nunca las palabras de otra persona


def test_el_texto_de_las_palabras_va_escapado(logged_client, user):
    _vocabulario(user, cuantas=4)
    db.session.add(Vocabulario(idUser=user.idUser, nombre='</script><b>x', significado='<img src=x>'))
    db.session.commit()
    html = logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True)
    assert '</script><b>x' not in html and '<img src=x>' not in html
    assert any(p['en'] == '</script><b>x' for p in _palabras_de_la_pagina(html))


def test_las_palabras_salen_al_azar_sin_pesos(logged_client, user):
    _vocabulario(user)
    datos = _palabras_de_la_pagina(logged_client.get('/menu/ingles/juegos/unir').get_data(as_text=True))
    assert all(set(p) == {'id', 'en', 'es'} for p in datos)
    js = logged_client.get('/static/js/juegos.js').get_data(as_text=True)
    # Bolsa guardada en el navegador: ninguna palabra se repite hasta que salgan todas
    assert 'juegosUnirPendientes' in js and 'localStorage' in js
    assert 'peso' not in js and 'XP' not in js


# ── Resultado de una ronda ──

def test_guardar_ronda_sin_xp(logged_client, user):
    ids = [p.idVocab for p in _vocabulario(user)][:6]
    for _ in range(5):
        respuesta = _enviar(logged_client, ids, errores=2, segundos=41)
        assert respuesta.status_code == 200 and respuesta.get_json() == {'success': True}
    partida = JuegoPartida.query.first()
    assert (partida.juego, partida.parejas, partida.errores, partida.segundos) == ('unir', 6, 2, 41)
    assert partida.precision == 75  # 6 aciertos de 8 intentos
    assert JuegoPartida.query.count() == 5
    assert _xp(user) == 0  # los juegos no tocan el nivel



def test_no_se_aceptan_palabras_de_otra_persona(logged_client, user, other_user):
    mias = [p.idVocab for p in _vocabulario(user)][:3]
    ajena = Vocabulario(idUser=other_user.idUser, nombre='x', significado='y')
    db.session.add(ajena)
    db.session.commit()
    assert _enviar(logged_client, mias + [ajena.idVocab]).status_code == 400
    assert JuegoPartida.query.count() == 0


def test_resultados_invalidos(logged_client, user):
    ids = [p.idVocab for p in _vocabulario(user)]
    malos = [
        {'ids': ids[:3], 'errores': 0, 'segundos': 10},          # menos del mínimo
        {'ids': ids[:7], 'errores': 0, 'segundos': 10},          # más de una ronda
        {'ids': ids[:3] + ids[:1], 'errores': 0, 'segundos': 10},  # repetidas
        {'ids': ids[:4], 'errores': -1, 'segundos': 10},
        {'ids': ids[:4], 'errores': 0, 'segundos': 99999},
        {'ids': ids[:4], 'errores': '2', 'segundos': 10},
        {'ids': 'todo', 'errores': 0, 'segundos': 10},
        {},
    ]
    for datos in malos:
        assert logged_client.post('/menu/ingles/juegos/unir/resultado', json=datos).status_code == 400, datos
    assert logged_client.post('/menu/ingles/juegos/otro/resultado', json={}).status_code == 404
    assert JuegoPartida.query.count() == 0


def test_menu_muestra_el_resumen(logged_client, user):
    ids = [p.idVocab for p in _vocabulario(user)][:4]
    _enviar(logged_client, ids, errores=0, segundos=20)
    _enviar(logged_client, ids, errores=4, segundos=12)
    html = logged_client.get('/menu/ingles/juegos/').get_data(as_text=True)
    assert '2</span> rondas' in html
    assert '75%</span> precisión' in html   # (100 + 50) / 2
    assert '20s</span> mejor ronda perfecta' in html  # solo cuentan las rondas sin errores
    assert 'XP' not in _sin_tokens(html)


def test_borrar_usuario_borra_sus_partidas(app, user):
    from app.routes.users_route import _delete_user_data
    db.session.add(JuegoPartida(idUser=user.idUser, juego='unir', parejas=4))
    db.session.commit()
    _delete_user_data(user.idUser)
    db.session.commit()
    assert JuegoPartida.query.count() == 0


# ═══════════════ Sopa de letras ═══════════════
import shutil
import subprocess
from pathlib import Path

import pytest

from app.routes.juegos_route import letras_para_sopa

SOPA = [('borrow', 'pedir prestado'), ('enough', 'suficiente'), ('although', 'aunque'),
        ('wear', 'llevar puesto'), ('learn', 'aprender'), ('break', 'romper'),
        ('give up', 'rendirse'), ("don't", 'no hacer')]


def _vocabulario_sopa(user, pares=SOPA):
    for en, es in pares:
        db.session.add(Vocabulario(idUser=user.idUser, nombre=en, significado=es))
    db.session.commit()
    return {p.nombre: p.idVocab for p in Vocabulario.query.filter_by(idUser=user.idUser).all()}


def _palabras_sopa(html):
    bloque = re.search(r'<script type="application/json" id="sopaPalabras">(.*?)</script>', html, re.S)
    return json.loads(bloque.group(1))


def _enviar_sopa(client, ids, **extra):
    datos = {'ids': ids, 'errores': 1, 'segundos': 60, 'pistas': 1, 'nivel': 'normal', **extra}
    return client.post('/menu/ingles/juegos/sopa/resultado', json=datos)


def test_que_palabras_sirven_para_la_sopa():
    assert letras_para_sopa('Borrow') == 'BORROW'
    assert letras_para_sopa('  café ') == 'CAFE'           # sin tildes
    assert letras_para_sopa('although') == 'ALTHOUGH'
    for mala in ('give up', "don't", 'well-known', 'go', 'understanding', 'R2D2', ''):
        assert letras_para_sopa(mala) is None, mala


def test_sopa_requiere_login(client):
    assert client.get('/menu/ingles/juegos/sopa').status_code == 302


def test_sopa_solo_manda_palabras_de_una_pieza(logged_client, user):
    _vocabulario_sopa(user)
    html = logged_client.get('/menu/ingles/juegos/sopa').get_data(as_text=True)
    assert 'id="juegoSopa"' in html and 'js/juegos.js' in html
    datos = _palabras_sopa(html)
    assert {p['letras'] for p in datos} == {'BORROW', 'ENOUGH', 'ALTHOUGH', 'WEAR', 'LEARN', 'BREAK'}
    assert all(set(p) == {'id', 'en', 'es', 'letras'} for p in datos)
    for nivel in ('facil', 'normal', 'dificil'):
        assert f'data-nivel="{nivel}"' in html


def test_sopa_pide_mas_palabras_si_no_alcanzan(logged_client, user):
    # 4 de una pieza + 2 frases: no alcanzan las 5 que pide la sopa
    _vocabulario_sopa(user, SOPA[:4] + SOPA[6:])
    html = logged_client.get('/menu/ingles/juegos/sopa').get_data(as_text=True)
    assert 'Necesitas al menos' in html and 'id="juegoSopa"' not in html
    assert 'Tienes 4 de 6' in html
    menu = logged_client.get('/menu/ingles/juegos/').get_data(as_text=True)
    assert 'Necesitas 5 palabras de una sola pieza (tienes 4)' in menu


def test_guardar_ronda_de_sopa(logged_client, user):
    ids = list(_vocabulario_sopa(user).values())[:6]
    respuesta = _enviar_sopa(logged_client, ids, errores=2, pistas=1, nivel='dificil', segundos=95)
    assert respuesta.status_code == 200 and respuesta.get_json() == {'success': True}
    partida = JuegoPartida.query.one()
    assert (partida.juego, partida.parejas, partida.errores, partida.pistas, partida.nivel, partida.segundos) == \
        ('sopa', 6, 2, 1, 'dificil', 95)
    assert _xp(user) == 0


def test_resultado_de_sopa_invalido(logged_client, user):
    ids = list(_vocabulario_sopa(user).values())[:6]
    for extra in ({'nivel': 'imposible'}, {'nivel': None}, {'pistas': -1}, {'pistas': 7}, {'pistas': '1'}):
        assert _enviar_sopa(logged_client, ids, **extra).status_code == 400, extra
    assert JuegoPartida.query.count() == 0


def test_unir_no_guarda_nivel_ni_pistas(logged_client, user):
    ids = [p.idVocab for p in _vocabulario(user)][:4]
    _enviar(logged_client, ids)
    partida = JuegoPartida.query.one()
    assert partida.nivel is None and partida.pistas == 0


def test_ronda_con_pistas_no_es_perfecta(logged_client, user):
    ids = list(_vocabulario_sopa(user).values())[:5]
    _enviar_sopa(logged_client, ids, errores=0, pistas=2, segundos=30)
    _enviar_sopa(logged_client, ids, errores=0, pistas=0, segundos=80)
    html = logged_client.get('/menu/ingles/juegos/').get_data(as_text=True)
    assert '80s</span> mejor ronda perfecta' in html  # la de 30s usó pistas


def test_esquema_agrega_columnas_nuevas_a_partidas():
    from pathlib import Path as P
    texto = (P(__file__).resolve().parent.parent / 'services' / 'esquema.py').read_text()
    assert "'juego_partidas': {'nivel': 'VARCHAR(10)', 'pistas': 'INTEGER NOT NULL DEFAULT 0'}" in texto


NODE = shutil.which('node')
SCRIPT_SOPA = r"""
const { generarSopa, buscarEnTablero, DIRECCIONES } = require(process.argv[1]);
const palabras = ['BORROW', 'ENOUGH', 'ALTHOUGH', 'WEAR', 'LEARN', 'BREAK', 'RUN', 'RUNNER', 'LEVEL', 'TEN']
    .map((letras, id) => ({ id, letras }));
const problemas = [];
let tableros = 0;
for (const nivel of Object.keys(DIRECCIONES)) {
  for (const n of [8, 10]) {
    for (let vez = 0; vez < 60; vez++) {
      const ronda = palabras.filter((p) => p.letras.length <= n).sort(() => Math.random() - 0.5).slice(0, 6);
      const sopa = generarSopa(ronda, n, DIRECCIONES[nivel]);
      if (!sopa) { problemas.push(`sin tablero ${nivel} ${n}`); continue; }
      tableros++;
      const { tablero, colocadas } = sopa;
      if (tablero.length !== n || tablero.some((f) => f.length !== n || f.some((l) => !/^[A-Z]$/.test(l)))) problemas.push('tablero mal lleno');
      if (colocadas.length < 4) problemas.push('menos de 4 palabras');
      const permitidas = new Set(DIRECCIONES[nivel].map((d) => d.join()));
      for (const { palabra, celdas } of colocadas) {
        if (celdas.map(([f, c]) => tablero[f][c]).join('') !== palabra.letras) problemas.push(`${palabra.letras} cortada`);
        const paso = [celdas[1][0] - celdas[0][0], celdas[1][1] - celdas[0][1]];
        if (!permitidas.has(paso.join())) problemas.push(`${palabra.letras} en dirección no permitida (${nivel})`);
        const lugares = new Set(buscarEnTablero(tablero, palabra.letras).map((cs) => cs.map(String).sort().join('|')));
        if (lugares.size !== 1) problemas.push(`${palabra.letras} aparece ${lugares.size} veces`);
        // Ninguna palabra puede quedar entera dentro de otra (RUN dentro de RUNNER)
        const propias = new Set(celdas.map(String));
        for (const otra of colocadas) {
          if (otra !== sopa.colocadas.find((x) => x.palabra === palabra) && celdas.every((c) => otra.celdas.map(String).includes(String(c)))) {
            problemas.push(`${palabra.letras} escondida dentro de ${otra.palabra.letras}`);
          }
        }
      }
    }
  }
}
console.log(JSON.stringify({ tableros, problemas: [...new Set(problemas)] }));
"""


@pytest.mark.skipif(NODE is None, reason='Node no está instalado')
def test_armado_de_la_sopa_nunca_corta_ni_repite_palabras(tmp_path):
    juegos_js = Path(__file__).resolve().parent.parent / 'static' / 'js' / 'juegos.js'
    salida = subprocess.run([NODE, '-e', SCRIPT_SOPA, str(juegos_js)], capture_output=True, text=True, timeout=120)
    assert salida.returncode == 0, salida.stderr
    resultado = json.loads(salida.stdout)
    assert resultado['tableros'] >= 350          # casi siempre logra armar el tablero
    assert resultado['problemas'] == []
