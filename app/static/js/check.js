const checkItems = document.querySelectorAll('.check-item[data-id]');
const progressFill = document.querySelector('.check-progress-fill');
const progressText = document.querySelector('.check-progress-text');

function updateProgress() {
    if (!progressText) return;
    const total = checkItems.length;
    const done = document.querySelectorAll('.check-item.done').length;
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    if (progressFill) progressFill.style.width = pct + '%';
    progressText.textContent = `${done} / ${total} completados hoy`;
}

// ── CUENTA REGRESIVA HASTA MEDIANOCHE (reinicio del check diario) ──
const countdownText = document.getElementById('countdownText');

function updateCountdown() {
    if (!countdownText) return;
    const now = new Date();
    const medianoche = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0);
    let diff = medianoche - now;

    if (diff <= 0) {
        countdownText.textContent = '00h 00m 00s';
        location.reload();
        return;
    }

    const horas = Math.floor(diff / 3600000);
    diff -= horas * 3600000;
    const minutos = Math.floor(diff / 60000);
    diff -= minutos * 60000;
    const segundos = Math.floor(diff / 1000);

    countdownText.textContent =
        `${String(horas).padStart(2, '0')}h ${String(minutos).padStart(2, '0')}m ${String(segundos).padStart(2, '0')}s`;
}

updateCountdown();
setInterval(updateCountdown, 1000);

checkItems.forEach(item => {
    item.addEventListener('click', () => {
        const id = item.dataset.id;
        item.style.pointerEvents = 'none';
        fetch(`/habit/${id}/toggle_today`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;
                item.classList.toggle('done', data.done);
                updateProgress();
            })
            .catch(() => alert('No se pudo actualizar el hábito.'))
            .finally(() => {
                item.style.pointerEvents = 'auto';
            });
    });
});
