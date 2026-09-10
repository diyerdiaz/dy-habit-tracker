const vocabSetupCard = document.getElementById('vocabSetupCard');
const vocabDeck = document.getElementById('vocabDeck');
const vocabCantidad = document.getElementById('vocabCantidad');
const vocabIniciarBtn = document.getElementById('vocabIniciarBtn');
const vocabCambiarCantidad = document.getElementById('vocabCambiarCantidad');
const vocabRevelarBtn = document.getElementById('vocabRevelarBtn');
const vocabFlashBack = document.getElementById('vocabFlashBack');
const vocabFlashcard = document.getElementById('vocabFlashcard');
const vocabSummary = document.getElementById('vocabSummary');
const vocabProgress = document.getElementById('vocabProgress');
const vocabReiniciarBtn = document.getElementById('vocabReiniciarBtn');

let vocabSesion = [];
let vocabIndice = 0;
let vocabStats = { facil: 0, medio: 0, dificil: 0 };

// Elige "cantidad" palabras al azar (ponderado por dificultad) dentro de un mismo grupo,
// sin repetir ninguna, hasta agotar ese grupo.
function vocabElegirDeGrupo(grupo, cantidad) {
    const disponibles = grupo.slice();
    const seleccion = [];

    while (seleccion.length < cantidad && disponibles.length > 0) {
        const pesoTotal = disponibles.reduce((suma, p) => suma + (p.peso || 1), 0);
        let punto = Math.random() * pesoTotal;
        let indice = 0;

        for (; indice < disponibles.length; indice++) {
            punto -= (disponibles[indice].peso || 1);
            if (punto <= 0) break;
        }
        indice = Math.min(indice, disponibles.length - 1);

        seleccion.push(disponibles[indice]);
        disponibles.splice(indice, 1);
    }

    return seleccion;
}

// Selección por rondas: ninguna palabra se repite hasta que todas hayan aparecido
// la misma cantidad de veces (se agrupan por "vecesMostrada" y se completa cada
// grupo, del que menos ha salido al que más, antes de pasar al siguiente).
// Dentro de cada grupo, las palabras más difíciles tienen más probabilidad de salir.
function vocabSeleccionPonderada(lista, cantidad) {
    const grupos = {};
    lista.forEach((p) => {
        const veces = p.vecesMostrada || 0;
        if (!grupos[veces]) grupos[veces] = [];
        grupos[veces].push({ ...p });
    });

    const nivelesOrdenados = Object.keys(grupos).map(Number).sort((a, b) => a - b);
    const seleccion = [];

    for (const nivel of nivelesOrdenados) {
        if (seleccion.length >= cantidad) break;
        const faltan = cantidad - seleccion.length;
        seleccion.push(...vocabElegirDeGrupo(grupos[nivel], faltan));
    }

    return seleccion;
}

function vocabMostrarDeck() {
    vocabSetupCard.style.display = 'none';
    vocabDeck.style.display = 'block';
    vocabDeck.style.opacity = '0';
    requestAnimationFrame(() => {
        vocabDeck.style.transition = 'opacity 0.5s ease';
        vocabDeck.style.opacity = '1';
    });
}

function vocabMostrarPalabra() {
    const palabra = vocabSesion[vocabIndice];

    vocabProgress.textContent = `Palabra ${vocabIndice + 1} de ${vocabSesion.length}`;
    document.getElementById('vocabFlashWord').textContent = palabra.nombre;
    document.getElementById('vocabFlashMeaning').textContent = palabra.significado;
    document.getElementById('vocabFlashExample').textContent = palabra.ejemplos ? `"${palabra.ejemplos}"` : '';

    vocabFlashBack.style.display = 'none';
    vocabRevelarBtn.style.display = '';
    vocabFlashcard.style.display = '';
    vocabSummary.style.display = 'none';
}

function vocabMostrarResumen() {
    vocabFlashcard.style.display = 'none';
    vocabSummary.style.display = '';
    document.getElementById('vocabSummaryText').textContent =
        `Fácil: ${vocabStats.facil} · Medio fácil: ${vocabStats.medio} · Difícil: ${vocabStats.dificil}`;
}

if (vocabIniciarBtn) {
    vocabIniciarBtn.addEventListener('click', () => {
        const cantidad = parseInt(vocabCantidad.value, 10);
        const todas = window.VOCAB_PALABRAS || [];

        vocabSesion = vocabSeleccionPonderada(todas, cantidad);
        vocabIndice = 0;
        vocabStats = { facil: 0, medio: 0, dificil: 0 };

        vocabMostrarDeck();
        vocabMostrarPalabra();
    });
}

if (vocabRevelarBtn) {
    vocabRevelarBtn.addEventListener('click', () => {
        vocabFlashBack.style.display = '';
        vocabRevelarBtn.style.display = 'none';
    });
}

document.querySelectorAll('.vocab-rating-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
        const rating = btn.dataset.rating;
        const palabra = vocabSesion[vocabIndice];
        vocabStats[rating] = (vocabStats[rating] || 0) + 1;

        fetch('/menu/ingles/vocabulario/calificar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                idVocab: palabra.idVocab,
                nombre: palabra.nombre,
                calificacion: rating
            })
        }).catch(() => {});

        vocabIndice++;
        if (vocabIndice >= vocabSesion.length) {
            vocabMostrarResumen();
        } else {
            vocabMostrarPalabra();
        }
    });
});

if (vocabReiniciarBtn) {
    vocabReiniciarBtn.addEventListener('click', () => {
        vocabDeck.style.display = 'none';
        vocabSetupCard.style.display = '';
    });
}

if (vocabCambiarCantidad) {
    vocabCambiarCantidad.addEventListener('click', (e) => {
        e.preventDefault();
        vocabDeck.style.display = 'none';
        vocabSetupCard.style.display = '';
    });
}

// Modales de la lista "Mis Palabras" (editar / eliminar)
function openVocabEditModal(id, nombre, significado, ejemplos) {
    document.getElementById('vocabEditForm').action = `/menu/ingles/vocabulario/${id}/editar`;
    document.getElementById('vocabEditNombre').value = nombre;
    document.getElementById('vocabEditSignificado').value = significado;
    document.getElementById('vocabEditEjemplos').value = ejemplos;
    var modal = new bootstrap.Modal(document.getElementById('vocabEditModal'));
    modal.show();
}

function openVocabDeleteModal(id, nombre) {
    document.getElementById('vocabDeleteForm').action = `/menu/ingles/vocabulario/${id}/eliminar`;
    document.getElementById('vocabDelNombre').textContent = nombre;
    var modal = new bootstrap.Modal(document.getElementById('vocabDeleteModal'));
    modal.show();
}

// Popup de detalle de día en el calendario de práctica
const vocabDayPopup = document.getElementById('vocabDayPopup');
if (vocabDayPopup) {
    const popupTitle = document.getElementById('vocabDayPopupTitle');
    const popupCount = document.getElementById('vocabDayPopupCount');
    const popupWords = document.getElementById('vocabDayPopupWords');

    document.querySelectorAll('.vocab-cal-day[data-fecha]').forEach((celda) => {
        if (celda.classList.contains('is-future')) return;
        celda.addEventListener('click', (e) => {
            e.stopPropagation();
            const label = celda.dataset.label;
            const count = parseInt(celda.dataset.count, 10) || 0;
            const palabras = celda.dataset.palabras || '';

            popupTitle.textContent = label;
            popupCount.textContent = count === 0
                ? 'Sin práctica registrada'
                : `${count} palabra${count !== 1 ? 's' : ''} practicada${count !== 1 ? 's' : ''}`;
            popupWords.textContent = palabras;

            const celdaRect = celda.getBoundingClientRect();
            const contenedor = document.getElementById('vocabCalScroll');
            const padreRect = contenedor.getBoundingClientRect();

            let left = celdaRect.left - padreRect.left + celdaRect.width / 2;
            const top = celdaRect.top - padreRect.top - 10;

            const maxLeft = padreRect.width - 130;
            left = Math.max(130, Math.min(left, maxLeft));

            vocabDayPopup.style.left = left + 'px';
            vocabDayPopup.style.top = top + 'px';
            vocabDayPopup.classList.add('visible');
        });
    });

    document.addEventListener('click', () => {
        vocabDayPopup.classList.remove('visible');
    });
    vocabDayPopup.addEventListener('click', (e) => e.stopPropagation());
}
