"""Calendarios de vocabulario y shadowing más grandes: los días tienen un tamaño
mínimo y, si no caben (celular), el calendario se desliza de lado y abre en hoy."""
import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / 'static'
CALENDARIOS = {
    '/menu/ingles/vocabulario/calendario': 'vocabDayPopup',
    '/menu/ingles/shadowing/calendario': 'shadowDayPopup',
}


@pytest.mark.parametrize('ruta,popup', CALENDARIOS.items())
def test_el_calendario_va_dentro_de_un_contenedor_deslizable(logged_client, ruta, popup):
    html = logged_client.get(ruta).get_data(as_text=True)
    inicio = html.index('class="vocab-cal-scroll"')
    # Meses y días van dentro; el detalle del día va fuera para que no lo recorte
    assert inicio < html.index('class="vocab-cal-months"') < html.index('class="vocab-cal-weeks"')
    assert html.index('class="vocab-cal-weeks"') < html.index(f'id="{popup}"')
    contenido = html[html.index('class="vocab-cal-calendar"'):html.index(f'id="{popup}"')]
    assert len(re.findall(r'<div\b', contenido)) == contenido.count('</div>') + 1  # solo queda abierto el calendario
    assert 'js/ingles.js' in html


def test_los_dias_tienen_tamano_minimo():
    css = (STATIC / 'css' / 'vocabulario.css').read_text()
    assert '--cell-min: 16px;' in css
    semana = css[css.index('.vocab-cal-week {'):]
    semana = semana[:semana.index('}')]
    assert 'flex: 1 0 var(--cell-min);' in semana and 'min-width: var(--cell-min);' in semana
    deslizable = css[css.index('.vocab-cal-scroll {'):]
    assert 'overflow-x: auto;' in deslizable[:deslizable.index('}')]


def test_en_pantallas_grandes_cabe_el_anio_entero():
    css = (STATIC / 'css' / 'vocabulario.css').read_text()
    grande = css[css.index('@media (min-width: 1280px)'):]
    assert 'width: 1100px;' in grande[:grande.index('}\n}')]


def test_abre_en_el_dia_de_hoy():
    js = (STATIC / 'js' / 'ingles.js').read_text()
    assert ".vocab-cal-day:not(.is-future)" in js
    assert 'scroll.scrollLeft =' in js
    # al deslizar se cierra el detalle del día
    assert "popup.classList.remove('visible')" in js
