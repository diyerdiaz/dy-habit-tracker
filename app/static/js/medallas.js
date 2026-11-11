document.querySelectorAll('.medallas-filtro').forEach(function (btn) {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.medallas-filtro').forEach(function (b) { b.classList.remove('activo'); });
        btn.classList.add('activo');
        var filtro = btn.dataset.filtro;
        var visibles = 0;
        document.querySelectorAll('.medalla-card').forEach(function (card) {
            var mostrar = filtro === 'todas'
                || (filtro === 'ganadas' && card.dataset.ganada === 'si')
                || (filtro === 'nuevas' && card.dataset.nueva === 'si')
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


// Anuncio de medallas nuevas: "Ver" filtra por las nuevas; "Cerrar", Escape o
// tocar fuera lo cierran.
(function () {
    var anuncio = document.getElementById('medallasAnuncio');
    if (!anuncio) return;

    function cerrar() {
        anuncio.remove();
        document.removeEventListener('keydown', alTeclear);
    }
    function alTeclear(e) {
        if (e.key === 'Escape') cerrar();
    }

    document.getElementById('medallasAnuncioCerrar').addEventListener('click', cerrar);
    document.getElementById('medallasAnuncioVer').addEventListener('click', function () {
        cerrar();
        var filtro = document.querySelector('.medallas-filtro[data-filtro="nuevas"]');
        if (filtro) {
            filtro.click();
            filtro.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
    anuncio.addEventListener('click', function (e) {
        if (e.target === anuncio) cerrar();
    });
    document.addEventListener('keydown', alTeclear);
    document.getElementById('medallasAnuncioVer').focus();
})();
