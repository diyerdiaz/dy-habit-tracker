const shadowHourglass = document.getElementById('shadowHourglass');
const shadowTimerDisplay = document.getElementById('shadowTimerDisplay');
const shadowStartBtn = document.getElementById('shadowStartBtn');
const shadowStopBtn = document.getElementById('shadowStopBtn');
const shadowResetBtn = document.getElementById('shadowResetBtn');
const shadowManualForm = document.getElementById('shadowManualForm');

let shadowSegundos = 0;
let shadowIntervalo = null;
let shadowCorriendo = false;

// Selector de modo: Cronómetro o Agregar Tiempo (uno a la vez, no apilados)
const shadowModeToggle = document.getElementById('shadowModeToggle');
const shadowTimerCard = document.getElementById('shadowTimerCard');

if (shadowModeToggle) {
    const opcionesModo = shadowModeToggle.querySelectorAll('.shadow-mode-option');
    opcionesModo.forEach((btn) => {
        btn.addEventListener('click', () => {
            const modo = btn.dataset.mode;
            opcionesModo.forEach((b) => b.classList.remove('active-side'));
            btn.classList.add('active-side');

            if (modo === 'manual') {
                shadowModeToggle.classList.add('mode-manual');
                shadowTimerCard.style.display = 'none';
                shadowManualForm.style.display = '';
            } else {
                shadowModeToggle.classList.remove('mode-manual');
                shadowTimerCard.style.display = '';
                shadowManualForm.style.display = 'none';
            }
        });
    });
}

function shadowFormatoTiempo(segundos) {
    const m = Math.floor(segundos / 60).toString().padStart(2, '0');
    const s = (segundos % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

function shadowGuardarSesion(segundos) {
    fetch('/menu/ingles/shadowing/guardar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segundos })
    }).then(() => window.location.reload());
}

if (shadowStartBtn) {
    shadowStartBtn.addEventListener('click', () => {
        if (shadowCorriendo) return;
        shadowCorriendo = true;
        shadowHourglass.classList.remove('paused');
        shadowStartBtn.style.display = 'none';
        shadowStopBtn.style.display = '';

        shadowIntervalo = setInterval(() => {
            shadowSegundos++;
            shadowTimerDisplay.textContent = shadowFormatoTiempo(shadowSegundos);
        }, 1000);
    });
}

if (shadowStopBtn) {
    shadowStopBtn.addEventListener('click', () => {
        shadowCorriendo = false;
        clearInterval(shadowIntervalo);
        shadowHourglass.classList.add('paused');
        shadowStopBtn.style.display = 'none';
        shadowStartBtn.style.display = '';

        if (shadowSegundos > 0) {
            shadowGuardarSesion(shadowSegundos);
        }
    });
}

if (shadowResetBtn) {
    shadowResetBtn.addEventListener('click', () => {
        clearInterval(shadowIntervalo);
        shadowCorriendo = false;
        shadowSegundos = 0;
        shadowTimerDisplay.textContent = '00:00';
        shadowHourglass.classList.add('paused');
        shadowStartBtn.style.display = '';
        shadowStopBtn.style.display = 'none';
    });
}

if (shadowManualForm) {
    shadowManualForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const min = parseInt(document.getElementById('shadowManualMin').value, 10) || 0;
        const seg = parseInt(document.getElementById('shadowManualSeg').value, 10) || 0;
        const total = (min * 60) + seg;

        if (total <= 0) return;
        shadowGuardarSesion(total);
    });
}

// Popup de detalle de día en el calendario de shadowing
const shadowDayPopup = document.getElementById('shadowDayPopup');
if (shadowDayPopup) {
    const popupTitle = document.getElementById('shadowDayPopupTitle');
    const popupCount = document.getElementById('shadowDayPopupCount');

    document.querySelectorAll('.vocab-cal-day[data-fecha]').forEach((celda) => {
        if (celda.classList.contains('is-future')) return;
        celda.addEventListener('click', (e) => {
            e.stopPropagation();
            const label = celda.dataset.label;
            const minutos = parseInt(celda.dataset.minutos, 10) || 0;

            popupTitle.textContent = label;
            popupCount.textContent = minutos === 0
                ? 'Sin práctica registrada'
                : `${minutos} minuto${minutos !== 1 ? 's' : ''} de shadowing`;

            const celdaRect = celda.getBoundingClientRect();
            const contenedor = document.getElementById('shadowCalScroll');
            const padreRect = contenedor.getBoundingClientRect();

            let left = celdaRect.left - padreRect.left + celdaRect.width / 2;
            const top = celdaRect.top - padreRect.top - 10;

            const maxLeft = padreRect.width - 130;
            left = Math.max(130, Math.min(left, maxLeft));

            shadowDayPopup.style.left = left + 'px';
            shadowDayPopup.style.top = top + 'px';
            shadowDayPopup.classList.add('visible');
        });
    });

    document.addEventListener('click', () => {
        shadowDayPopup.classList.remove('visible');
    });
    shadowDayPopup.addEventListener('click', (e) => e.stopPropagation());
}

// Modales del registro de sesiones (editar / eliminar)
function openShadowEditModal(id, minutos, segundos) {
    document.getElementById('shadowEditForm').action = `/menu/ingles/shadowing/${id}/editar`;
    document.getElementById('shadowEditMinutos').value = minutos;
    document.getElementById('shadowEditSegundos').value = segundos;
    var modal = new bootstrap.Modal(document.getElementById('shadowEditModal'));
    modal.show();
}

function openShadowDeleteModal(id, label) {
    document.getElementById('shadowDeleteForm').action = `/menu/ingles/shadowing/${id}/eliminar`;
    document.getElementById('shadowDelLabel').textContent = label;
    var modal = new bootstrap.Modal(document.getElementById('shadowDeleteModal'));
    modal.show();
}
