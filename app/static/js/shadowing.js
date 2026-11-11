// ── Temporizador de Shadowing: cronómetro, cuenta regresiva y tiempo manual ──
const shadowReloj = document.getElementById('shadowReloj');
const shadowRelojAvance = document.getElementById('shadowRelojAvance');
const shadowTimerDisplay = document.getElementById('shadowTimerDisplay');
const shadowStartBtn = document.getElementById('shadowStartBtn');
const shadowStopBtn = document.getElementById('shadowStopBtn');
const shadowResetBtn = document.getElementById('shadowResetBtn');
const shadowManualForm = document.getElementById('shadowManualForm');
const shadowModeToggle = document.getElementById('shadowModeToggle');
const shadowTimerCard = document.getElementById('shadowTimerCard');
const shadowCuentaConfig = document.getElementById('shadowCuentaConfig');
const shadowCuentaMinutos = document.getElementById('shadowCuentaMinutos');
const shadowAlarmaAviso = document.getElementById('shadowAlarmaAviso');
const shadowAlarmaTexto = document.getElementById('shadowAlarmaTexto');
const shadowAlarmaBtn = document.getElementById('shadowAlarmaBtn');

// Largo del anillo (2 * PI * r, con r = 52 en el SVG)
const SHADOW_CIRCUNFERENCIA = 2 * Math.PI * 52;
const SHADOW_MAX_MINUTOS = 180;
const SHADOW_CLAVE_MINUTOS = 'shadowCuentaMinutos';

let shadowModo = 'timer';        // 'timer' | 'regresiva' | 'manual'
let shadowCorriendo = false;
let shadowIntervalo = null;
let shadowSegundos = 0;          // cronómetro: segundos transcurridos
let shadowDuracion = 0;          // regresiva: duración elegida en segundos
let shadowRestante = 0;          // regresiva: segundos que faltan
let shadowFin = 0;               // regresiva: momento (ms) en que termina

function shadowFormatoTiempo(segundos) {
    const m = Math.floor(segundos / 60).toString().padStart(2, '0');
    const s = (segundos % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

// Pinta el anillo lleno en la fracción indicada (0 a 1).
// sinAnimacion: salta directo, sin la transición de 1 s.
function shadowPintarAnillo(fraccion, sinAnimacion) {
    if (!shadowRelojAvance) return;
    if (sinAnimacion) {
        shadowRelojAvance.style.transition = 'none';
        shadowRelojAvance.style.strokeDashoffset = SHADOW_CIRCUNFERENCIA * (1 - fraccion);
        shadowRelojAvance.getBoundingClientRect();  // aplica el salto antes de volver a animar
        shadowRelojAvance.style.transition = '';
        return;
    }
    shadowRelojAvance.style.strokeDashoffset = SHADOW_CIRCUNFERENCIA * (1 - fraccion);
}

// Cronómetro: el anillo da una vuelta completa por minuto; a los 60 s queda
// lleno y al empezar el minuto siguiente vuelve a vacío sin animarse hacia atrás.
function shadowActualizarReloj(segundos) {
    const enMinuto = segundos % 60;
    const fraccion = (segundos > 0 && enMinuto === 0) ? 1 : enMinuto / 60;
    if (enMinuto === 1 || segundos === 0) shadowPintarAnillo(0, true);
    shadowPintarAnillo(fraccion);
}

function shadowGuardarSesion(segundos, recargar = true) {
    return fetch('/menu/ingles/shadowing/guardar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ segundos })
    }).then((r) => {
        if (recargar) window.location.reload();
        return r.ok;
    }).catch(() => false);
}

// ── Duración de la cuenta regresiva ──
function shadowLeerMinutosGuardados() {
    try {
        const v = parseInt(localStorage.getItem(SHADOW_CLAVE_MINUTOS), 10);
        return (v >= 1 && v <= SHADOW_MAX_MINUTOS) ? v : 20;
    } catch (e) {
        return 20;
    }
}

function shadowMinutosElegidos() {
    const v = parseInt(shadowCuentaMinutos ? shadowCuentaMinutos.value : '', 10);
    if (!v || v < 1) return 1;
    return Math.min(v, SHADOW_MAX_MINUTOS);
}

function shadowElegirMinutos(minutos) {
    if (shadowCuentaMinutos) shadowCuentaMinutos.value = minutos;
    document.querySelectorAll('.shadow-cuenta-chip').forEach((chip) => {
        chip.classList.toggle('activo', parseInt(chip.dataset.minutos, 10) === minutos);
    });
    try { localStorage.setItem(SHADOW_CLAVE_MINUTOS, String(minutos)); } catch (e) { /* sin almacenamiento */ }
    if (shadowModo === 'regresiva' && !shadowCorriendo) shadowPrepararRegresiva();
}

// Deja el reloj lleno con la duración elegida, listo para iniciar
function shadowPrepararRegresiva() {
    shadowDuracion = shadowMinutosElegidos() * 60;
    shadowRestante = shadowDuracion;
    shadowTimerDisplay.textContent = shadowFormatoTiempo(shadowRestante);
    shadowReloj.classList.remove('terminado');
    shadowPintarAnillo(1, true);
}

function shadowPrepararCronometro() {
    shadowSegundos = 0;
    shadowTimerDisplay.textContent = '00:00';
    shadowReloj.classList.remove('terminado');
    shadowActualizarReloj(0);
}

if (shadowCuentaConfig) {
    document.querySelectorAll('.shadow-cuenta-chip').forEach((chip) => {
        chip.addEventListener('click', () => shadowElegirMinutos(parseInt(chip.dataset.minutos, 10)));
    });
    shadowCuentaMinutos.addEventListener('input', () => {
        const v = parseInt(shadowCuentaMinutos.value, 10);
        if (v >= 1 && v <= SHADOW_MAX_MINUTOS) shadowElegirMinutos(v);
    });
    shadowCuentaMinutos.addEventListener('change', () => shadowElegirMinutos(shadowMinutosElegidos()));
    shadowElegirMinutos(shadowLeerMinutosGuardados());
}

// ── Selector de modo (uno a la vez; bloqueado mientras corre el reloj) ──
if (shadowModeToggle) {
    const opcionesModo = shadowModeToggle.querySelectorAll('.shadow-mode-option');
    opcionesModo.forEach((btn) => {
        btn.addEventListener('click', () => {
            if (shadowCorriendo || shadowAlarmaSonando) return;
            shadowModo = btn.dataset.mode;
            opcionesModo.forEach((b) => b.classList.remove('active-side'));
            btn.classList.add('active-side');

            shadowModeToggle.classList.toggle('mode-regresiva', shadowModo === 'regresiva');
            shadowModeToggle.classList.toggle('mode-manual', shadowModo === 'manual');
            shadowTimerCard.style.display = shadowModo === 'manual' ? 'none' : '';
            shadowManualForm.style.display = shadowModo === 'manual' ? '' : 'none';
            if (shadowCuentaConfig) shadowCuentaConfig.hidden = shadowModo !== 'regresiva';

            if (shadowModo === 'regresiva') shadowPrepararRegresiva();
            else if (shadowModo === 'timer') shadowPrepararCronometro();
        });
    });
}

// ── Pantalla encendida mientras corre (solo donde el navegador lo permite) ──
let shadowWakeLock = null;
async function shadowMantenerPantalla() {
    try {
        if ('wakeLock' in navigator) shadowWakeLock = await navigator.wakeLock.request('screen');
    } catch (e) { /* no disponible (p. ej. sin HTTPS): se sigue igual */ }
}
function shadowSoltarPantalla() {
    if (shadowWakeLock) { shadowWakeLock.release().catch(() => {}); shadowWakeLock = null; }
}
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && shadowCorriendo) {
        shadowMantenerPantalla();
        if (shadowModo === 'regresiva') shadowTickRegresiva();  // se pone al día al volver
    }
});

// ── Alarma: pitidos generados con Web Audio (sin archivos de sonido) ──
let shadowAudio = null;
let shadowAlarmaSonando = false;
let shadowAlarmaIntervalo = null;
let shadowAlarmaCorte = null;

// El audio solo se puede activar con un toque del usuario: se prepara al Iniciar
function shadowPrepararAudio() {
    const Contexto = window.AudioContext || window.webkitAudioContext;
    if (!Contexto) return;
    if (!shadowAudio) shadowAudio = new Contexto();
    if (shadowAudio.state === 'suspended') shadowAudio.resume();
}

function shadowPitido(inicio, frecuencia) {
    const osc = shadowAudio.createOscillator();
    const vol = shadowAudio.createGain();
    osc.type = 'square';
    osc.frequency.value = frecuencia;
    vol.gain.setValueAtTime(0.0001, inicio);
    vol.gain.exponentialRampToValueAtTime(0.25, inicio + 0.02);
    vol.gain.exponentialRampToValueAtTime(0.0001, inicio + 0.18);
    osc.connect(vol).connect(shadowAudio.destination);
    osc.start(inicio);
    osc.stop(inicio + 0.2);
}

function shadowSonarRonda() {
    if (shadowAudio) {
        const t = shadowAudio.currentTime + 0.05;
        shadowPitido(t, 880);
        shadowPitido(t + 0.25, 880);
        shadowPitido(t + 0.5, 1175);
    }
    if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 400]);
}

function shadowIniciarAlarma() {
    shadowAlarmaSonando = true;
    shadowSonarRonda();
    shadowAlarmaIntervalo = setInterval(shadowSonarRonda, 1500);
    // Si nadie la apaga, deja de sonar sola al minuto
    shadowAlarmaCorte = setTimeout(shadowApagarSonido, 60000);
}

function shadowApagarSonido() {
    clearInterval(shadowAlarmaIntervalo);
    clearTimeout(shadowAlarmaCorte);
    if (navigator.vibrate) navigator.vibrate(0);
}

if (shadowAlarmaBtn) {
    shadowAlarmaBtn.addEventListener('click', () => {
        shadowApagarSonido();
        shadowAlarmaSonando = false;
        window.location.reload();  // la sesión ya se guardó: se actualizan los totales
    });
}

// ── Cuenta regresiva ──
function shadowTickRegresiva() {
    const restante = Math.max(0, Math.ceil((shadowFin - Date.now()) / 1000));
    if (restante === shadowRestante && restante > 0) return;
    shadowRestante = restante;
    shadowTimerDisplay.textContent = shadowFormatoTiempo(restante);
    shadowPintarAnillo(restante / shadowDuracion);
    if (restante === 0) shadowTerminarRegresiva();
}

function shadowTerminarRegresiva() {
    clearInterval(shadowIntervalo);
    shadowCorriendo = false;
    shadowSoltarPantalla();
    shadowModeToggle.classList.remove('bloqueado');
    shadowReloj.classList.add('paused', 'terminado');
    shadowStopBtn.style.display = 'none';
    shadowStartBtn.style.display = 'none';
    shadowResetBtn.style.display = 'none';

    const minutos = Math.round(shadowDuracion / 60);
    shadowAlarmaTexto.textContent = `¡Terminaste tus ${minutos} minuto${minutos !== 1 ? 's' : ''} de shadowing!`;
    shadowAlarmaAviso.hidden = false;
    shadowIniciarAlarma();

    // Se guarda ya, sin recargar, para no cortar la alarma
    shadowGuardarSesion(shadowDuracion, false).then((ok) => {
        if (!ok) shadowAlarmaTexto.textContent += ' (no se pudo guardar la sesión)';
    });
}

// ── Botones ──
if (shadowStartBtn) {
    shadowStartBtn.addEventListener('click', () => {
        if (shadowCorriendo) return;
        shadowCorriendo = true;
        shadowReloj.classList.remove('paused');
        shadowModeToggle.classList.add('bloqueado');
        shadowStartBtn.style.display = 'none';
        shadowStopBtn.style.display = '';
        shadowMantenerPantalla();

        if (shadowModo === 'regresiva') {
            shadowPrepararAudio();
            if (shadowCuentaConfig) shadowCuentaConfig.hidden = true;
            shadowPrepararRegresiva();
            shadowFin = Date.now() + shadowDuracion * 1000;
            shadowIntervalo = setInterval(shadowTickRegresiva, 250);
            return;
        }

        shadowIntervalo = setInterval(() => {
            shadowSegundos++;
            shadowTimerDisplay.textContent = shadowFormatoTiempo(shadowSegundos);
            shadowActualizarReloj(shadowSegundos);
        }, 1000);
    });
}

if (shadowStopBtn) {
    shadowStopBtn.addEventListener('click', () => {
        shadowCorriendo = false;
        clearInterval(shadowIntervalo);
        shadowSoltarPantalla();
        shadowModeToggle.classList.remove('bloqueado');
        shadowReloj.classList.add('paused');
        shadowStopBtn.style.display = 'none';
        shadowStartBtn.style.display = '';

        // En la cuenta regresiva se guarda lo que alcanzó a practicar
        const practicado = shadowModo === 'regresiva' ? shadowDuracion - shadowRestante : shadowSegundos;
        if (practicado > 0) shadowGuardarSesion(practicado);
        else if (shadowModo === 'regresiva' && shadowCuentaConfig) shadowCuentaConfig.hidden = false;
    });
}

if (shadowResetBtn) {
    shadowResetBtn.addEventListener('click', () => {
        clearInterval(shadowIntervalo);
        shadowCorriendo = false;
        shadowSoltarPantalla();
        shadowModeToggle.classList.remove('bloqueado');
        shadowReloj.classList.add('paused');
        shadowStartBtn.style.display = '';
        shadowStopBtn.style.display = 'none';

        if (shadowModo === 'regresiva') {
            if (shadowCuentaConfig) shadowCuentaConfig.hidden = false;
            shadowPrepararRegresiva();
        } else {
            shadowPrepararCronometro();
        }
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
