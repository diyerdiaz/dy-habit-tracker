document.querySelectorAll('.medallas-filtro').forEach(function (btn) {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.medallas-filtro').forEach(function (b) { b.classList.remove('activo'); });
        btn.classList.add('activo');
        var filtro = btn.dataset.filtro;
        var visibles = 0;
        document.querySelectorAll('.medalla-card').forEach(function (card) {
            var mostrar = filtro === 'todas'
                || (filtro === 'ganadas' && card.dataset.ganada === 'si')
                || card.dataset.categoria === filtro;
            card.hidden = !mostrar;
            if (mostrar) visibles++;
        });
        // Oculta las secciones que quedaron sin tarjetas visibles
        document.querySelectorAll('.medallas-seccion').forEach(function (sec) {
            sec.hidden = !sec.querySelector('.medalla-card:not([hidden])');
        });
        document.getElementById('medallasVacio').hidden = visibles > 0;
    });
});
