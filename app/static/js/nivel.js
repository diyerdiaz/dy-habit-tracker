// Mi Nivel Personal: cambia entre el panel "Mi nivel" y el mapa de "Niveles"
document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.nivel-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(otro => {
                const activo = otro === tab;
                otro.classList.toggle('activo', activo);
                otro.setAttribute('aria-selected', activo ? 'true' : 'false');
                document.getElementById(otro.dataset.panel).hidden = !activo;
            });
        });
    });
});
