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
const vocabTiempo = document.getElementById('vocabTiempo');
const vocabTerminarBtn = document.getElementById('vocabTerminarBtn');
const vocabEspera = document.getElementById('vocabEspera');

let vocabSesion = [];
let vocabIndice = 0;
let vocabStats = { facil: 0, medio: 0, dificil: 0 };
let vocabMinimoSeg = 0;        // tiempo mínimo en cada tarjeta
let vocabInicioTarjeta = 0;    // cuándo se mostró la tarjeta actual
let vocabTemporizador = null;
let vocabPuedePasar = true;
const VOCAB_PESOS = { dificil: 3, medio: 2, facil: 1 };
const VOCAB_CLAVE_TIEMPO = 'vocab-tiempo-tarjeta';

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

// Turnos: ninguna palabra se repite hasta que todas hayan aparecido la misma
// cantidad de veces (se agrupan por "vecesMostrada" y se completa cada grupo,
// del que menos ha salido al que más, antes de pasar al siguiente). Dentro de
// cada grupo, las palabras más difíciles tienen más probabilidad de salir.
function vocabPorTurnos(lista, cantidad) {
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

// Arma la ronda: primero las palabras cuya última calificación fue "Difícil"
// (vuelven en cada ronda hasta que se marquen más fáciles) y después el resto
// por turnos. Ninguna palabra se repite dentro de la misma ronda.
function vocabSeleccionPonderada(lista, cantidad) {
    const dificiles = lista.filter((p) => p.ultimaCalificacion === 'dificil');
    const resto = lista.filter((p) => p.ultimaCalificacion !== 'dificil');

    const seleccion = vocabPorTurnos(dificiles, cantidad);
    seleccion.push(...vocabPorTurnos(resto, cantidad - seleccion.length));
    return seleccion;
}

// Al calificar, la palabra se actualiza también en la página: si se arma otra
// ronda sin recargar (o se sale a mitad), ya cuenta lo que se acaba de estudiar.
function vocabRegistrarCalificacion(palabras, idVocab, calificacion) {
    const palabra = palabras.find((p) => p.idVocab === idVocab);
    if (!palabra) return null;
    palabra.vecesMostrada = (palabra.vecesMostrada || 0) + 1;
    palabra.ultimaCalificacion = calificacion;
    palabra.peso = VOCAB_PESOS[calificacion] || 2;
    return palabra;
}

// Segundos que faltan para poder pasar de tarjeta (0 = ya se puede)
function vocabSegundosRestantes(inicioMs, ahoraMs, minimoSeg) {
    return Math.max(0, Math.ceil(minimoSeg - (ahoraMs - inicioMs) / 1000));
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

function vocabDetenerTemporizador() {
    clearInterval(vocabTemporizador);
    vocabTemporizador = null;
}

function vocabBotonesCalificar(activos) {
    vocabPuedePasar = activos;
    document.querySelectorAll('.vocab-rating-btn').forEach((b) => { b.disabled = !activos; });
}

// Cuenta regresiva del tiempo mínimo. Empieza al pulsar "Ver significado"
// (el tiempo que se pasa aprendiéndolo); hasta que llegue a 0 no se puede calificar.
function vocabIniciarTemporizador() {
    vocabDetenerTemporizador();
    vocabInicioTarjeta = Date.now();
    if (vocabMinimoSeg <= 0) {
        vocabEspera.hidden = true;
        vocabBotonesCalificar(true);
        return;
    }
    vocabBotonesCalificar(false);
    vocabEspera.hidden = false;
    const fill = document.getElementById('vocabEsperaFill');
    const texto = document.getElementById('vocabEsperaTexto');

    const actualizar = () => {
        const ahora = Date.now();
        const faltan = vocabSegundosRestantes(vocabInicioTarjeta, ahora, vocabMinimoSeg);
        const avance = Math.min(1, (ahora - vocabInicioTarjeta) / (vocabMinimoSeg * 1000));
        fill.style.width = `${Math.round(avance * 100)}%`;
        if (faltan > 0) {
            texto.textContent = `Apréndete el significado: podrás pasar en ${faltan} s`;
            return;
        }
        vocabDetenerTemporizador();
        vocabEspera.hidden = true;
        vocabBotonesCalificar(true);
    };
    actualizar();
    vocabTemporizador = setInterval(actualizar, 200);
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
    vocabTerminarBtn.style.display = '';
    // El tiempo todavía no corre: empieza al ver el significado
    vocabDetenerTemporizador();
    vocabEspera.hidden = true;
    vocabBotonesCalificar(false);
}

// Resumen al terminar la ronda o al salir antes con "Terminar aquí": muestra
// las que de verdad se estudiaron (ya quedaron guardadas una por una).
function vocabMostrarResumen() {
    vocabDetenerTemporizador();
    const estudiadas = vocabIndice;
    const total = vocabSesion.length;
    vocabFlashcard.style.display = 'none';
    vocabTerminarBtn.style.display = 'none';
    vocabSummary.style.display = '';
    vocabProgress.textContent = `Estudiaste ${estudiadas} de ${total}`;

    const titulo = document.getElementById('vocabSummaryTitulo');
    const texto = document.getElementById('vocabSummaryText');
    if (estudiadas >= total) {
        titulo.textContent = '¡Sesión completada!';
    } else if (estudiadas > 0) {
        titulo.textContent = 'Sesión guardada';
    } else {
        titulo.textContent = 'No calificaste ninguna palabra';
        texto.textContent = 'No se guardó nada. Cuando quieras, empieza otra vez.';
        return;
    }
    const plural = estudiadas === 1 ? 'palabra estudiada' : 'palabras estudiadas';
    texto.textContent = `${estudiadas} de ${total} ${plural} y guardadas. ` +
        `Fácil: ${vocabStats.facil} · Medio fácil: ${vocabStats.medio} · Difícil: ${vocabStats.dificil}`;
}

function vocabVolverAlInicio() {
    vocabDetenerTemporizador();
    vocabDeck.style.display = 'none';
    vocabSetupCard.style.display = '';
}

// Recuerda en este navegador el último tiempo elegido
if (vocabTiempo) {
    try {
        const guardado = localStorage.getItem(VOCAB_CLAVE_TIEMPO);
        if (guardado !== null && vocabTiempo.querySelector(`option[value="${guardado}"]`)) vocabTiempo.value = guardado;
    } catch (e) { /* sin almacenamiento: se usa el de por defecto */ }
    vocabTiempo.addEventListener('change', () => {
        try { localStorage.setItem(VOCAB_CLAVE_TIEMPO, vocabTiempo.value); } catch (e) { /* no pasa nada */ }
    });
}

if (vocabIniciarBtn) {
    vocabIniciarBtn.addEventListener('click', () => {
        const cantidad = parseInt(vocabCantidad.value, 10);
        const todas = window.VOCAB_PALABRAS || [];

        vocabMinimoSeg = Math.max(0, parseInt(vocabTiempo ? vocabTiempo.value : '0', 10) || 0);
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
        vocabIniciarTemporizador();
    });
}

document.querySelectorAll('.vocab-rating-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
        if (!vocabPuedePasar) return;  // todavía no se cumple el tiempo mínimo
        const rating = btn.dataset.rating;
        const palabra = vocabSesion[vocabIndice];
        vocabStats[rating] = (vocabStats[rating] || 0) + 1;

        // Se guarda en el momento (keepalive: aunque se salga de la página enseguida)
        fetch('/menu/ingles/vocabulario/calificar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            keepalive: true,
            body: JSON.stringify({
                idVocab: palabra.idVocab,
                nombre: palabra.nombre,
                calificacion: rating
            })
        }).catch(() => {});
        vocabRegistrarCalificacion(window.VOCAB_PALABRAS || [], palabra.idVocab, rating);

        vocabIndice++;
        if (vocabIndice >= vocabSesion.length) {
            vocabMostrarResumen();
        } else {
            vocabMostrarPalabra();
        }
    });
});

if (vocabTerminarBtn) {
    vocabTerminarBtn.addEventListener('click', vocabMostrarResumen);
}

if (vocabReiniciarBtn) {
    vocabReiniciarBtn.addEventListener('click', vocabVolverAlInicio);
}

if (vocabCambiarCantidad) {
    vocabCambiarCantidad.addEventListener('click', (e) => {
        e.preventDefault();
        vocabVolverAlInicio();
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

// Para probar la selección de la ronda con node (en el navegador no hace nada)
if (typeof module !== 'undefined') {
    module.exports = { vocabSeleccionPonderada, vocabPorTurnos, vocabRegistrarCalificacion, vocabSegundosRestantes };
}
