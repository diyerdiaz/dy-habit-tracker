const tareasList = document.getElementById('tareasList');
const tareasEmpty = document.getElementById('tareasEmpty');
const addForm = document.getElementById('addTaskForm');
const newTaskInput = document.getElementById('newTaskInput');

function updateEmptyState() {
    const hasTareas = tareasList.querySelector('.tarea-item') !== null;
    tareasList.style.display = hasTareas ? '' : 'none';
    tareasEmpty.style.display = hasTareas ? 'none' : '';
}

// ── Fecha de la tarea: Hoy, Mañana u otra del calendario ──
const fechaSelector = document.getElementById('fechaSelector');
const fechaOtraChip = document.getElementById('fechaOtraChip');
const fechaOtraTexto = document.getElementById('fechaOtraTexto');
const proximasPanel = document.getElementById('proximasPanel');
const mananaLista = document.getElementById('mananaLista');
const HOY = fechaSelector.dataset.hoy;
const MANANA = fechaSelector.dataset.manana;
const MAXIMA = fechaSelector.dataset.maxima;
let fechaElegida = HOY;

// ── Calendario grande ──
const calendarioPanel = document.getElementById('calendarioPanel');
const calDias = document.getElementById('calDias');
const calMes = document.getElementById('calMes');
const calAyuda = document.getElementById('calAyuda');
const calAnterior = document.getElementById('calAnterior');
const calSiguiente = document.getElementById('calSiguiente');
const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
               'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const DIAS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
let conteos = {};
try { conteos = JSON.parse(calendarioPanel.dataset.conteos || '{}'); } catch (e) { conteos = {}; }

// Las fechas se manejan como texto AAAA-MM-DD para no depender de la zona horaria
const aIso = (a, m, d) => `${a}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
const [hoyA, hoyM] = HOY.split('-').map(Number);
const [maxA, maxM] = MAXIMA.split('-').map(Number);
let vistaA = hoyA, vistaM = hoyM - 1;

function textoFecha(iso) {
    if (iso === HOY) return 'hoy';
    if (iso === MANANA) return 'mañana';
    const [a, m, d] = iso.split('-').map(Number);
    return `${DIAS[new Date(a, m - 1, d).getDay()].toLowerCase()} ${d} de ${MESES[m - 1].toLowerCase()}`;
}

function pintarCalendario() {
    calMes.textContent = `${MESES[vistaM]} ${vistaA}`;
    calAnterior.disabled = vistaA === hoyA && vistaM === hoyM - 1;
    calSiguiente.disabled = vistaA === maxA && vistaM === maxM - 1;

    calDias.innerHTML = '';
    const huecos = (new Date(vistaA, vistaM, 1).getDay() + 6) % 7;  // la semana empieza en lunes
    for (let i = 0; i < huecos; i++) calDias.appendChild(document.createElement('span'));

    const totalDias = new Date(vistaA, vistaM + 1, 0).getDate();
    for (let d = 1; d <= totalDias; d++) {
        const iso = aIso(vistaA, vistaM, d);
        const dia = document.createElement('button');
        dia.type = 'button';
        dia.className = 'tareas-cal-dia';
        dia.dataset.fecha = iso;
        dia.innerHTML = `<span class="tareas-cal-num">${d}</span>`;
        if (iso < HOY || iso > MAXIMA) dia.disabled = true;
        if (iso === HOY) dia.classList.add('hoy');
        if (iso === fechaElegida) dia.classList.add('elegido');
        const n = conteos[iso] || 0;
        if (n) {
            const marca = document.createElement('span');
            marca.className = 'tareas-cal-marca';
            marca.textContent = n;
            marca.title = `${n} tarea${n === 1 ? '' : 's'}`;
            dia.appendChild(marca);
        }
        dia.addEventListener('click', () => elegirFecha(iso));
        calDias.appendChild(dia);
    }
    calAyuda.textContent = `Agregando tareas para ${textoFecha(fechaElegida)}. Escribe la tarea arriba.`;
}

function elegirFecha(iso) {
    fechaElegida = iso;
    const chip = fechaSelector.querySelector(`button.tareas-fecha-chip[data-fecha="${iso}"]`);
    fechaSelector.querySelectorAll('.tareas-fecha-chip').forEach(c => c.classList.toggle('activo', c === (chip || fechaOtraChip)));
    if (chip) {
        fechaOtraTexto.textContent = 'Otra fecha';
    } else {
        const [a, m, d] = iso.split('-');
        fechaOtraTexto.textContent = `${d}/${m}/${a}`;
    }
    pintarCalendario();
    newTaskInput.focus();
}

function sumarConteo(iso, cambio) {
    conteos[iso] = Math.max(0, (conteos[iso] || 0) + cambio);
    if (!conteos[iso]) delete conteos[iso];
    pintarCalendario();
}

fechaSelector.querySelectorAll('button.tareas-fecha-chip[data-fecha]').forEach(chip => {
    chip.addEventListener('click', () => elegirFecha(chip.dataset.fecha));
});

fechaOtraChip.addEventListener('click', () => {
    const abrir = calendarioPanel.hidden;
    calendarioPanel.hidden = !abrir;
    fechaOtraChip.setAttribute('aria-expanded', String(abrir));
    if (abrir) {
        const [a, m] = fechaElegida.split('-').map(Number);
        vistaA = a; vistaM = m - 1;
        pintarCalendario();
    }
});

calAnterior.addEventListener('click', () => {
    vistaM -= 1;
    if (vistaM < 0) { vistaM = 11; vistaA -= 1; }
    pintarCalendario();
});

calSiguiente.addEventListener('click', () => {
    vistaM += 1;
    if (vistaM > 11) { vistaM = 0; vistaA += 1; }
    pintarCalendario();
});

// Mismo HTML que templates/tareas/_tarea_item.html
function crearItem(id, descripcion) {
    const item = document.createElement('div');
    item.className = 'tarea-item';
    item.dataset.id = id;
    item.dataset.hora = '';
    item.innerHTML = `
        <div class="tarea-circle"><i class="bi bi-check-lg"></i></div>
        <div class="tarea-cuerpo">
            <div class="tarea-text"></div>
            <span class="tarea-hora" hidden><i class="bi bi-bell-fill"></i> <span class="tarea-hora-texto"></span></span>
        </div>
        <div class="tarea-acciones">
            <button type="button" class="tarea-btn tarea-recordar" title="Recordatorio por correo" aria-label="Recordatorio por correo"><i class="bi bi-bell"></i></button>
            <button type="button" class="tarea-btn tarea-editar" title="Editar" aria-label="Editar tarea"><i class="bi bi-pencil"></i></button>
            <button type="button" class="tarea-delete" title="Eliminar" aria-label="Eliminar tarea"><i class="bi bi-trash"></i></button>
        </div>
    `;
    item.querySelector('.tarea-text').textContent = descripcion;
    attachTareaHandlers(item);
    return item;
}

// ── Avisos cortos arriba del formulario ──
const tareasAviso = document.getElementById('tareasAviso');
let avisoTimer = null;
function avisar(texto, tipo = 'ok') {
    tareasAviso.textContent = texto;
    tareasAviso.className = `tareas-aviso ${tipo}`;
    tareasAviso.hidden = false;
    clearTimeout(avisoTimer);
    avisoTimer = setTimeout(() => { tareasAviso.hidden = true; }, 6000);
}

function postForm(url, datos) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(datos).toString()
    }).then(res => res.json());
}

// ── Editar el texto de la tarea ──
function editarTarea(item) {
    if (item.classList.contains('editando')) return;
    cerrarRecordatorio(item);
    const texto = item.querySelector('.tarea-text');
    const original = texto.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'tarea-edit-input';
    input.maxLength = 255;
    input.value = original;
    input.setAttribute('aria-label', 'Editar tarea');
    item.classList.add('editando');
    texto.hidden = true;
    texto.after(input);
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);

    let terminado = false;
    const terminar = (guardar) => {
        if (terminado) return;
        terminado = true;
        const nuevo = input.value.trim();
        const restaurar = () => { input.remove(); texto.hidden = false; item.classList.remove('editando'); };
        if (!guardar || !nuevo || nuevo === original) { restaurar(); return; }
        postForm(`/tareas/${item.dataset.id}/editar`, { descripcion: nuevo })
            .then(data => {
                if (data.success) texto.textContent = data.descripcion;
                else avisar(data.error || 'No se pudo editar la tarea.', 'error');
            })
            .catch(() => avisar('No se pudo editar la tarea.', 'error'))
            .finally(restaurar);
    };
    input.addEventListener('click', e => e.stopPropagation());
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); terminar(true); }
        if (e.key === 'Escape') terminar(false);
    });
    input.addEventListener('blur', () => terminar(true));
}

// ── Recordatorio por correo a una hora ──
function cerrarRecordatorio(item) {
    const panel = item.querySelector('.tarea-recordatorio');
    if (panel) panel.remove();
    item.classList.remove('con-panel');
}

function mostrarHora(item, hora, horaTexto) {
    item.dataset.hora = hora || '';
    const etiqueta = item.querySelector('.tarea-hora');
    etiqueta.hidden = !hora;
    etiqueta.querySelector('.tarea-hora-texto').textContent = horaTexto || '';
    item.querySelector('.tarea-recordar i').className = hora ? 'bi bi-bell-fill' : 'bi bi-bell';
}

function guardarRecordatorio(item, hora) {
    postForm(`/tareas/${item.dataset.id}/recordatorio`, { hora })
        .then(data => {
            if (!data.success) { avisar(data.error || 'No se pudo guardar el recordatorio.', 'error'); return; }
            mostrarHora(item, data.hora, data.horaTexto);
            cerrarRecordatorio(item);
            if (!data.hora) avisar('Recordatorio quitado.');
            else if (data.sinCorreo) avisar('Recordatorio guardado, pero no tienes correo: agrégalo en Mi Perfil para recibirlo.', 'error');
            else if (!data.correoActivo) avisar('Recordatorio guardado. El envío de correos no está configurado en este servidor.', 'error');
            else avisar(`🔔 Te enviaremos un correo a las ${data.horaTexto} si la tarea sigue pendiente.`);
        })
        .catch(() => avisar('No se pudo guardar el recordatorio.', 'error'));
}

function abrirRecordatorio(item) {
    if (item.querySelector('.tarea-recordatorio')) { cerrarRecordatorio(item); return; }
    document.querySelectorAll('.tarea-item.con-panel').forEach(cerrarRecordatorio);
    const panel = document.createElement('div');
    panel.className = 'tarea-recordatorio';
    panel.innerHTML = `
        <label class="tarea-rec-label"><i class="bi bi-envelope"></i> Avisarme por correo a las</label>
        <input type="time" class="tarea-rec-hora" aria-label="Hora del recordatorio">
        <button type="button" class="tarea-rec-guardar">Guardar</button>
        <button type="button" class="tarea-rec-quitar"${item.dataset.hora ? '' : ' hidden'}>Quitar</button>
    `;
    const input = panel.querySelector('.tarea-rec-hora');
    input.value = item.dataset.hora || '';
    panel.addEventListener('click', e => e.stopPropagation());
    panel.querySelector('.tarea-rec-guardar').addEventListener('click', () => {
        if (!input.value) { input.focus(); return; }
        guardarRecordatorio(item, input.value);
    });
    panel.querySelector('.tarea-rec-quitar').addEventListener('click', () => guardarRecordatorio(item, ''));
    input.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); panel.querySelector('.tarea-rec-guardar').click(); } });
    item.appendChild(panel);
    item.classList.add('con-panel');
    input.focus();
}

// La lista de "Tareas de mañana" se oculta cuando queda vacía
function actualizarProximas() {
    proximasPanel.hidden = !mananaLista.querySelector('.tarea-item');
}

function attachTareaHandlers(item) {
    const id = item.dataset.id;

    item.addEventListener('click', () => {
        if (item.classList.contains('editando')) return;
        fetch(`/tareas/${id}/toggle`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;
                item.classList.toggle('done', data.completada);
            })
            .catch(() => alert('No se pudo actualizar la tarea.'));
    });

    item.querySelector('.tarea-editar').addEventListener('click', (e) => {
        e.stopPropagation();
        editarTarea(item);
    });

    item.querySelector('.tarea-recordar').addEventListener('click', (e) => {
        e.stopPropagation();
        abrirRecordatorio(item);
    });

    item.querySelector('.tarea-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        if (!confirm('¿Eliminar esta tarea?')) return;
        fetch(`/tareas/${id}/delete`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;
                const grupo = item.closest('.tareas-proximas-dia');
                sumarConteo(grupo ? grupo.dataset.fecha : HOY, -1);
                item.remove();
                updateEmptyState();
                actualizarProximas();
            })
            .catch(() => alert('No se pudo eliminar la tarea.'));
    });
}

document.querySelectorAll('.tarea-item').forEach(attachTareaHandlers);

addForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const descripcion = newTaskInput.value.trim();
    if (!descripcion) return;

    fetch('/tareas/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'descripcion=' + encodeURIComponent(descripcion) + '&fecha=' + encodeURIComponent(fechaElegida)
    })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                alert(data.error || 'No se pudo agregar la tarea.');
                return;
            }
            const item = crearItem(data.id, data.descripcion);
            sumarConteo(data.fecha, 1);
            if (data.esHoy) {
                tareasList.appendChild(item);
                updateEmptyState();
            } else if (data.fecha === MANANA) {
                mananaLista.appendChild(item);
                proximasPanel.hidden = false;
                const grupo = mananaLista.parentElement;
                grupo.classList.remove('nuevo');
                void grupo.offsetWidth;
                grupo.classList.add('nuevo');
            } else {
                // Días más lejanos: no se listan, quedan marcados en el calendario
                calAyuda.textContent = `✓ Tarea agregada para ${textoFecha(data.fecha)}. Puedes escribir otra.`;
            }

            newTaskInput.value = '';
            newTaskInput.focus();
        })
        .catch(() => alert('No se pudo agregar la tarea.'));
});

// ── Ver Historial ──
const toggleHistBtn = document.getElementById('toggleHistBtn');
const historialPanel = document.getElementById('historialPanel');
const historialSelect = document.getElementById('historialSelect');

if (toggleHistBtn && historialPanel) {
    toggleHistBtn.addEventListener('click', () => {
        const abierto = historialPanel.classList.toggle('open');
        document.querySelector('.tareas-wrapper').classList.toggle('viendo-historial', abierto);
        toggleHistBtn.innerHTML = abierto
            ? '<i class="bi bi-eye-slash"></i> Ocultar Historial'
            : '<i class="bi bi-clock-history"></i> Ver Historial';
        if (abierto) {
            historialPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
}

if (historialSelect) {
    historialSelect.addEventListener('change', () => {
        document.querySelectorAll('.tareas-hist-day').forEach(dia => {
            dia.style.display = dia.dataset.fecha === historialSelect.value ? '' : 'none';
        });
    });
}
