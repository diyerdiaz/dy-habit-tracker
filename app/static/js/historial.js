document.addEventListener('DOMContentLoaded', () => {
    const popup = document.getElementById('dayPopup');
    const titleEl = document.getElementById('dayPopupTitle');
    const countEl = document.getElementById('dayPopupCount');
    const habitsEl = document.getElementById('dayPopupHabits');
    if (!popup) return;

    document.querySelectorAll('.hist-day[data-fecha]').forEach(cell => {
        if (cell.classList.contains('is-future')) return;
        cell.addEventListener('click', (e) => {
            e.stopPropagation();
            const label = cell.dataset.label;
            const count = parseInt(cell.dataset.count, 10) || 0;
            const habitos = cell.dataset.habitos || '';

            titleEl.textContent = label;
            countEl.textContent = count === 0
                ? 'Sin actividad registrada'
                : `${count} actividad${count !== 1 ? 'es' : ''} realizada${count !== 1 ? 's' : ''}`;
            habitsEl.textContent = habitos;

            const cellRect = cell.getBoundingClientRect();
            const container = document.getElementById('histScroll');
            const parentRect = container.getBoundingClientRect();

            let left = cellRect.left - parentRect.left + cellRect.width / 2;
            const top = cellRect.top - parentRect.top - 10;

            const maxLeft = parentRect.width - 130;
            left = Math.max(130, Math.min(left, maxLeft));

            popup.style.left = left + 'px';
            popup.style.top = top + 'px';
            popup.classList.add('visible');
        });
    });

    document.addEventListener('click', () => {
        popup.classList.remove('visible');
    });
    popup.addEventListener('click', (e) => e.stopPropagation());
});
