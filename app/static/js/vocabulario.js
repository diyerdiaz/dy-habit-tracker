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
const vocabAnteriorBtn = document.getElementById('vocabAnteriorBtn');
const vocabCorregirUltimaBtn = document.getElementById('vocabCorregirUltimaBtn');
const vocabCorrigiendo = document.getElementById('vocabCorrigiendo');

let vocabSesion = [];
let vocabIndice = 0;
// Calificación de cada tarjeta de la ronda (por posición), para poder volver
// atrás y corregirla: { rating, idRegistro } (idRegistro es una promesa)
let vocabRespuestas = [];
let vocabMinimoSeg = 0;        // tiempo mínimo en cada tarjeta
let vocabInicioTarjeta = 0;    // cuándo se mostró la tarjeta actual
let vocabTemporizador = null;
let vocabPuedePasar = true;
const VOCAB_PESOS = { dificil: 3, medio: 2, facil: 1 };
const VOCAB_CLAVE_TIEMPO = 'vocab-tiempo-tarjeta';
const VOCAB_NOMBRES = { facil: 'Fácil', medio: 'Medio fácil', dificil: 'Difícil' };

// Inglés (/menu/ingles/vocabulario) y Español (/menu/espanol/vocabulario) usan este
// mismo archivo: las peticiones van a la sección de la página que está abierta
function vocabUrl(ruta) {
    const camino = typeof location !== 'undefined' ? location.pathname : '';
    const i = camino.indexOf('/vocabulario');
    const base = i >= 0 ? camino.slice(0, i) + '/vocabulario' : '/menu/ingles/vocabulario';
    return base + ruta;
}

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
    // Lo que ya se practicó hoy no vuelve a salir hasta mañana
    const pendientes = vocabPendientesHoy(lista);
    const dificiles = pendientes.filter((p) => p.ultimaCalificacion === 'dificil');
    const resto = pendientes.filter((p) => p.ultimaCalificacion !== 'dificil');

    const seleccion = vocabPorTurnos(dificiles, cantidad);
    seleccion.push(...vocabPorTurnos(resto, cantidad - seleccion.length));
    return seleccion;
}

// Palabras que aún no se han practicado hoy
function vocabPendientesHoy(lista) {
    return lista.filter((p) => !p.estudiadaHoy);
}

// Al calificar, la palabra se actualiza también en la página: si se arma otra
// ronda sin recargar (o se sale a mitad), ya cuenta lo que se acaba de estudiar.
function vocabRegistrarCalificacion(palabras, idVocab, calificacion) {
    const palabra = palabras.find((p) => p.idVocab === idVocab);
    if (!palabra) return null;
    palabra.vecesMostrada = (palabra.vecesMostrada || 0) + 1;
    palabra.estudiadaHoy = true;
    palabra.ultimaCalificacion = calificacion;
    palabra.peso = VOCAB_PESOS[calificacion] || 2;
    return palabra;
}

// Corregir una calificación (se le dio al botón equivocado): cambia la dificultad
// de la palabra pero no cuenta como una vez más que salió.
function vocabCorregirCalificacion(palabras, idVocab, calificacion) {
    const palabra = palabras.find((p) => p.idVocab === idVocab);
    if (!palabra) return null;
    palabra.ultimaCalificacion = calificacion;
    palabra.peso = VOCAB_PESOS[calificacion] || 2;
    return palabra;
}

// Cuántas Fácil / Medio / Difícil quedaron en la ronda (ya con las correcciones)
function vocabContarCalificaciones(respuestas) {
    const stats = { facil: 0, medio: 0, dificil: 0 };
    respuestas.forEach((r) => { if (r && r.rating in stats) stats[r.rating]++; });
    return stats;
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
    const respuesta = vocabRespuestas[vocabIndice];

    vocabProgress.textContent = `Palabra ${vocabIndice + 1} de ${vocabSesion.length}`;
    document.getElementById('vocabFlashWord').textContent = palabra.nombre;
    document.getElementById('vocabFlashMeaning').textContent = palabra.significado;
    document.getElementById('vocabFlashExample').textContent = palabra.ejemplos ? `"${palabra.ejemplos}"` : '';

    vocabFlashBack.style.display = 'none';
    vocabRevelarBtn.style.display = '';
    vocabFlashcard.style.display = '';
    vocabSummary.style.display = 'none';
    vocabTerminarBtn.style.display = '';
    vocabAnteriorBtn.hidden = vocabIndice === 0;
    document.querySelectorAll('.vocab-rating-btn').forEach((b) => {
        b.classList.toggle('vocab-rating-elegida', !!respuesta && b.dataset.rating === respuesta.rating);
    });
    // El tiempo todavía no corre: empieza al ver el significado
    vocabDetenerTemporizador();
    vocabEspera.hidden = true;

    if (respuesta) {
        // Tarjeta ya calificada (se volvió con "Anterior"): se ve abierta y se puede corregir ya
        vocabFlashBack.style.display = '';
        vocabRevelarBtn.style.display = 'none';
        vocabCorrigiendo.hidden = false;
        vocabCorrigiendo.textContent = `Le pusiste "${VOCAB_NOMBRES[respuesta.rating]}". Elige otra para corregirla o la misma para seguir.`;
        vocabBotonesCalificar(true);
        return;
    }
    vocabCorrigiendo.hidden = true;
    vocabBotonesCalificar(false);
}

// Resumen al terminar la ronda o al salir antes con "Terminar aquí": muestra
// las que de verdad se estudiaron (ya quedaron guardadas una por una).
function vocabMostrarResumen() {
    vocabDetenerTemporizador();
    const estudiadas = vocabRespuestas.filter(Boolean).length;
    const total = vocabSesion.length;
    const vocabStats = vocabContarCalificaciones(vocabRespuestas);
    vocabFlashcard.style.display = 'none';
    vocabTerminarBtn.style.display = 'none';
    vocabAnteriorBtn.hidden = true;
    vocabCorregirUltimaBtn.hidden = estudiadas === 0;
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

// Al volver de una ronda: cuántas faltan hoy y la lista de cantidades.
// Si ya se practicaron todas, se avisa que vuelven mañana.
function vocabActualizarSetup() {
    const todas = window.VOCAB_PALABRAS || [];
    const pendientes = vocabPendientesHoy(todas).length;
    const controles = document.getElementById('vocabSetupControles');
    const todasHechas = document.getElementById('vocabTodasHechas');
    const texto = document.getElementById('vocabPendientesTexto');
    if (!controles || !todasHechas || !vocabCantidad) return;

    controles.hidden = pendientes === 0;
    todasHechas.hidden = pendientes !== 0;
    if (texto) {
        const plural = todas.length === 1 ? 'palabra' : 'palabras';
        texto.innerHTML = `Hoy te faltan <strong>${pendientes}</strong> de <strong>${todas.length}</strong> ${plural}. ` +
            'Las que ya practicaste hoy vuelven mañana.';
    }
    vocabCantidad.innerHTML = '';
    for (let n = 1; n <= pendientes; n++) {
        const opcion = document.createElement('option');
        opcion.value = String(n);
        opcion.textContent = `${n} palabra${n === 1 ? '' : 's'}`;
        opcion.selected = n === pendientes;
        vocabCantidad.appendChild(opcion);
    }
}

function vocabVolverAlInicio() {
    vocabDetenerTemporizador();
    vocabDeck.style.display = 'none';
    vocabActualizarSetup();
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
        vocabRespuestas = [];

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
        const anterior = vocabRespuestas[vocabIndice];

        if (anterior) {
            // Corrección: se cambia el mismo registro (no cuenta como otra vista)
            if (anterior.rating !== rating) {
                anterior.rating = rating;
                anterior.idRegistro.then((id) => {
                    if (!id) return;
                    fetch(vocabUrl(`/calificar/${id}/corregir`), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        keepalive: true,
                        body: JSON.stringify({ calificacion: rating })
                    }).catch(() => {});
                });
                vocabCorregirCalificacion(window.VOCAB_PALABRAS || [], palabra.idVocab, rating);
            }
        } else {
            // Se guarda en el momento (keepalive: aunque se salga de la página enseguida)
            const idRegistro = fetch(vocabUrl('/calificar'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                keepalive: true,
                body: JSON.stringify({
                    idVocab: palabra.idVocab,
                    nombre: palabra.nombre,
                    calificacion: rating
                })
            }).then((r) => (r.ok ? r.json() : null))
              .then((d) => (d && d.idRegistro) || null)
              .catch(() => null);
            vocabRespuestas[vocabIndice] = { rating, idRegistro };
            vocabRegistrarCalificacion(window.VOCAB_PALABRAS || [], palabra.idVocab, rating);
        }

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

// "Anterior": vuelve a la tarjeta de antes para corregir su calificación
if (vocabAnteriorBtn) {
    vocabAnteriorBtn.addEventListener('click', () => {
        if (vocabIndice === 0) return;
        vocabIndice--;
        vocabMostrarPalabra();
    });
}

// Desde el resumen: volver a la última tarjeta calificada
if (vocabCorregirUltimaBtn) {
    vocabCorregirUltimaBtn.addEventListener('click', () => {
        const ultima = vocabRespuestas.length - 1;
        if (ultima < 0) return;
        vocabIndice = ultima;
        vocabMostrarPalabra();
    });
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
    document.getElementById('vocabEditForm').action = vocabUrl(`/${id}/editar`);
    document.getElementById('vocabEditNombre').value = nombre;
    document.getElementById('vocabEditSignificado').value = significado;
    document.getElementById('vocabEditEjemplos').value = ejemplos;
    var modal = new bootstrap.Modal(document.getElementById('vocabEditModal'));
    modal.show();
}

function openVocabDeleteModal(id, nombre) {
    document.getElementById('vocabDeleteForm').action = vocabUrl(`/${id}/eliminar`);
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

// Agregar palabra: "Autocompletar" llena el significado (casa / hogar) y una
// frase de ejemplo. La búsqueda la hace el servidor; aquí solo se pide.
const vocabAutocompletarBtn = document.getElementById('vocabAutocompletarBtn');
if (vocabAutocompletarBtn) {
    const nombre = document.getElementById('vocabAddNombre');
    const significado = document.getElementById('vocabAddSignificado');
    const ejemplos = document.getElementById('vocabAddEjemplos');
    const estado = document.getElementById('vocabAutocompletarEstado');

    const mostrarEstado = (texto, esError) => {
        estado.hidden = false;
        estado.textContent = texto;
        estado.classList.toggle('es-error', !!esError);
    };

    vocabAutocompletarBtn.addEventListener('click', async () => {
        const palabra = nombre.value.trim();
        if (!palabra) {
            mostrarEstado('Primero escribe la palabra en inglés.', true);
            nombre.focus();
            return;
        }
        vocabAutocompletarBtn.disabled = true;
        vocabAutocompletarBtn.classList.add('is-buscando');
        mostrarEstado('Buscando significado y ejemplo…', false);
        try {
            const resp = await fetch(vocabUrl('/autocompletar'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ palabra })
            });
            const datos = await resp.json().catch(() => ({}));
            if (!resp.ok || !datos.success) {
                mostrarEstado(datos.error || 'No se pudo autocompletar. Escríbelo a mano.', true);
                return;
            }
            significado.value = datos.significado;
            ejemplos.value = datos.ejemplo;
            mostrarEstado(datos.ejemplo
                ? 'Listo. Revísalo y cámbialo si quieres antes de guardar.'
                : 'Significado listo. No se encontró un ejemplo: escríbelo tú si quieres.', false);
        } catch (e) {
            mostrarEstado('Sin conexión. Escríbelo a mano.', true);
        } finally {
            vocabAutocompletarBtn.disabled = false;
            vocabAutocompletarBtn.classList.remove('is-buscando');
        }
    });
}

// Para probar la selección de la ronda con node (en el navegador no hace nada)
if (typeof module !== 'undefined') {
    module.exports = {
        vocabSeleccionPonderada, vocabPorTurnos, vocabRegistrarCalificacion, vocabSegundosRestantes,
        vocabPendientesHoy, vocabUrl,
        vocabCorregirCalificacion, vocabContarCalificaciones,
    };
}
