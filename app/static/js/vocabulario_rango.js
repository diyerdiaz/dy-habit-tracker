// Mi Rango de Vocabulario: cambia entre "Rango de vocabulario" y "Rango de dominio"
document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.vocab-rank-tab');

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            tabs.forEach((otro) => {
                const activo = otro === tab;
                otro.classList.toggle('activo', activo);
                otro.setAttribute('aria-selected', activo ? 'true' : 'false');
                document.getElementById(otro.dataset.panel).hidden = !activo;
            });
        });
    });
});
