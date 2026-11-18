"""Agregar vocabulario: "Autocompletar" llena significado (MyMemory) y una frase
de ejemplo (Tatoeba). Aquí nunca se llama a internet: se simulan las respuestas."""
import pytest

from app.services import diccionario

RUTA = '/menu/ingles/vocabulario/autocompletar'

# Respuestas reales recortadas de las dos APIs para "house"
MYMEMORY_HOUSE = {
    'responseData': {'translatedText': 'albergar', 'match': 1},
    'quotaFinished': False,
    'matches': [
        {'segment': 'house', 'translation': 'albergar', 'match': 1, 'usage-count': 2},
        {'segment': 'house', 'translation': 'casa', 'match': 0.99, 'usage-count': 2},
        {'segment': 'house', 'translation': 'casa', 'match': 0.99, 'usage-count': 2},
        {'segment': 'big house', 'translation': 'casa grande', 'match': 0.7, 'usage-count': 1},
    ],
}
TATOEBA_HOUSE = {
    'results': [
        {'text': 'House is a great doctor.', 'translations': [[{'lang': 'spa', 'text': 'House es buen médico.'}], []]},
        {'text': 'Her house is big.', 'translations': [[], [{'lang': 'spa', 'text': 'Él está cansado.'}]]},
        {'text': 'Dad bought this house.', 'translations': [[{'lang': 'spa', 'text': 'Papá compró esta casa.'}], []]},
    ],
}


@pytest.fixture(autouse=True)
def _limpio(monkeypatch):
    diccionario.reiniciar_usos()
    monkeypatch.delenv('DICCIONARIO_LIMITE_DIARIO', raising=False)
    yield
    diccionario.reiniciar_usos()


@pytest.fixture
def apis(monkeypatch):
    """Simula MyMemory y Tatoeba y guarda las palabras consultadas."""
    estado = {'mymemory': MYMEMORY_HOUSE, 'tatoeba': TATOEBA_HOUSE, 'consultas': []}

    def mymemory(palabra):
        estado['consultas'].append(palabra)
        if isinstance(estado['mymemory'], Exception):
            raise estado['mymemory']
        return estado['mymemory']

    def tatoeba(palabra):
        if isinstance(estado['tatoeba'], Exception):
            raise estado['tatoeba']
        return estado['tatoeba']

    monkeypatch.setattr(diccionario, '_consultar_mymemory', mymemory)
    monkeypatch.setattr(diccionario, '_consultar_tatoeba', tatoeba)
    return estado


# ── Ruta ──

def test_llena_significado_con_barras_y_ejemplo_en_ingles(logged_client, apis):
    resp = logged_client.post(RUTA, json={'palabra': '  house '})
    assert resp.status_code == 200
    assert resp.get_json() == {
        'success': True,
        'significado': 'casa / albergar',
        'ejemplo': 'Dad bought this house.',   # solo la oración en inglés, sin traducción
    }
    assert apis['consultas'] == ['house']


def test_acepta_expresiones(logged_client, apis):
    for palabra in ['give up', 'well-known', "don't"]:
        assert logged_client.post(RUTA, json={'palabra': palabra}).status_code == 200


def test_pide_iniciar_sesion(client, apis):
    resp = client.post(RUTA, json={'palabra': 'house'})
    assert resp.status_code in (302, 401)
    assert apis['consultas'] == []


@pytest.mark.parametrize('palabra', ['', '   ', '123', 'house; drop table', 'a' * 61, '<script>', None])
def test_rechaza_textos_que_no_son_una_palabra(logged_client, apis, palabra):
    resp = logged_client.post(RUTA, json={'palabra': palabra})
    assert resp.status_code == 400 and resp.get_json()['success'] is False
    assert apis['consultas'] == []   # ni se consulta afuera


def test_limite_diario_por_usuario(logged_client, apis, monkeypatch):
    monkeypatch.setenv('DICCIONARIO_LIMITE_DIARIO', '2')
    assert logged_client.post(RUTA, json={'palabra': 'house'}).status_code == 200
    assert logged_client.post(RUTA, json={'palabra': 'dog'}).status_code == 200
    resp = logged_client.post(RUTA, json={'palabra': 'cat'})
    assert resp.status_code == 429 and 'límite' in resp.get_json()['error']
    assert apis['consultas'] == ['house', 'dog']


def test_si_falla_tatoeba_igual_da_el_significado(logged_client, apis):
    apis['tatoeba'] = TimeoutError('tatoeba lento')
    resp = logged_client.post(RUTA, json={'palabra': 'house'})
    assert resp.status_code == 200
    assert resp.get_json()['significado'] == 'casa / albergar'
    assert resp.get_json()['ejemplo'] == ''


def test_si_falla_mymemory_lo_dice(logged_client, apis):
    apis['mymemory'] = OSError('sin red')
    resp = logged_client.post(RUTA, json={'palabra': 'house'})
    assert resp.status_code == 502 and 'conexión' in resp.get_json()['error']


def test_cuota_gratis_agotada(logged_client, apis):
    apis['mymemory'] = {**MYMEMORY_HOUSE, 'quotaFinished': True}
    resp = logged_client.post(RUTA, json={'palabra': 'house'})
    assert resp.status_code == 502 and 'cuota' in resp.get_json()['error']


def test_sin_traduccion_lo_dice(logged_client, apis):
    apis['mymemory'] = {'responseData': {'translatedText': 'qwzx'}, 'matches': []}
    apis['mymemory']['responseData']['translatedText'] = 'qwzx'
    apis['tatoeba'] = {'results': []}
    resp = logged_client.post(RUTA, json={'palabra': 'qwzx'})
    assert resp.status_code == 502 and 'No se encontró' in resp.get_json()['error']


# ── Cómo se eligen significados y ejemplos ──

def test_suben_los_significados_que_salen_en_las_frases():
    assert diccionario.significados_de(MYMEMORY_HOUSE, 'house') == ['casa', 'albergar']
    # "albergar" sube si aparece en el ejemplo
    assert diccionario.significados_de(MYMEMORY_HOUSE, 'house', ['Puedo albergar a tres.'])[0] == 'albergar'


def test_separa_por_comas_quita_repetidos_y_deja_maximo_cuatro():
    datos = {'responseData': {'translatedText': 'carrera'}, 'matches': [
        {'segment': 'run', 'translation': 'demanda, pánico bancario', 'match': 1, 'usage-count': 0},
        {'segment': 'run', 'translation': 'Carrera.', 'match': 1, 'usage-count': 0},
        {'segment': 'run', 'translation': 'tramo', 'match': 0.9, 'usage-count': 0},
        {'segment': 'run', 'translation': 'correr', 'match': 0.8, 'usage-count': 0},
    ]}
    resultado = diccionario.significados_de(datos, 'run', ['¿Corres? Me gusta correr.'])
    assert resultado[0] == 'correr'
    assert len(resultado) == 4 and len(set(resultado)) == 4
    assert 'carrera' in resultado and 'demanda' in resultado


def test_ejemplos_solo_con_traduccion_directa_y_sin_nombres_propios():
    assert diccionario.ejemplos_de(TATOEBA_HOUSE, 'house') == [
        ('Dad bought this house.', 'Papá compró esta casa.'),
    ]


def test_la_palabra_debe_estar_completa_en_la_frase():
    datos = {'results': [
        {'text': 'The household is large.', 'translations': [[{'lang': 'spa', 'text': 'El hogar es grande.'}]]},
    ]}
    assert diccionario.ejemplos_de(datos, 'house') == []


# ── Página ──

def test_el_formulario_tiene_el_boton(logged_client):
    html = logged_client.get('/menu/ingles/vocabulario').get_data(as_text=True)
    assert 'id="vocabAutocompletarBtn"' in html and 'Autocompletar' in html
    assert 'id="vocabAddSignificado"' in html and 'id="vocabAddEjemplos"' in html
    assert 'js/vocabulario.js' in html


def test_el_boton_es_redondo_y_va_dentro_del_campo(logged_client):
    """El campo de la palabra ocupa todo el ancho y el botón es un círculo pequeño adentro."""
    html = logged_client.get('/menu/ingles/vocabulario').get_data(as_text=True)
    fila = html[html.index('class="vocab-autocompletar-fila"'):]
    fila = fila[:fila.index('</div>')]
    assert 'id="vocabAddNombre"' in fila and 'id="vocabAutocompletarBtn"' in fila
    assert 'bi-search' in fila and 'aria-label="Autocompletar significado y ejemplo"' in fila
    assert 'btn-vocab-accent' not in fila   # ya no es el botón grande con texto

    css = (diccionario.__file__.rsplit('/services/', 1)[0] + '/static/css/vocabulario.css')
    css = open(css, encoding='utf-8').read()
    regla = css[css.index('.vocab-autocompletar-btn {'):]
    regla = regla[:regla.index('}')]
    assert 'position: absolute' in regla and 'border-radius: 50%' in regla
    assert 'width: 32px' in regla and 'height: 32px' in regla
