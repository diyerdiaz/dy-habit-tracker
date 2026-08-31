const tareasList = document.getElementById('tareasList');
const tareasEmpty = document.getElementById('tareasEmpty');
const addForm = document.getElementById('addTaskForm');
const newTaskInput = document.getElementById('newTaskInput');

function updateEmptyState() {
    const hasTareas = tareasList.querySelector('.tarea-item') !== null;
    tareasList.style.display = hasTareas ? '' : 'none';
    tareasEmpty.style.display = hasTareas ? 'none' : '';
}

function attachTareaHandlers(item) {
    const id = item.dataset.id;

    item.addEventListener('click', () => {
        fetch(`/tareas/${id}/toggle`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;
                item.classList.toggle('done', data.completada);
            })
            .catch(() => alert('No se pudo actualizar la tarea.'));
    });

    item.querySelector('.tarea-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        if (!confirm('¿Eliminar esta tarea?')) return;
        fetch(`/tareas/${id}/delete`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;
                item.remove();
                updateEmptyState();
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
        body: 'descripcion=' + encodeURIComponent(descripcion)
    })
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            const item = document.createElement('div');
            item.className = 'tarea-item';
            item.dataset.id = data.id;
            item.innerHTML = `
                <div class="tarea-circle"><i class="bi bi-check-lg"></i></div>
                <div class="tarea-text"></div>
                <button type="button" class="tarea-delete" title="Eliminar">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            item.querySelector('.tarea-text').textContent = data.descripcion;

            tareasList.appendChild(item);
            attachTareaHandlers(item);
            updateEmptyState();

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
