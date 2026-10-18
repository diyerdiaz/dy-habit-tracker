// Animación de entrada a la cueva: deja la página borrosa mientras dura,
// la descubre al final y permite saltarla con el botón, un clic o Esc.
(function () {
    var cueva = document.getElementById('entradaCueva');
    if (!cueva) return;
    // Fuera de <main>: así no le afectan el desenfoque ni el zoom que se aplican a la página
    document.body.appendChild(cueva);
    document.body.classList.add('cueva-activa');

    var terminada = false;
    function terminar() {
        if (terminada) return;
        terminada = true;
        document.body.classList.remove('cueva-activa');
        cueva.style.transition = 'opacity 0.5s ease';
        cueva.style.opacity = '0';
        setTimeout(function () { cueva.remove(); }, 550);
    }

    // La luz llena la pantalla a los ~3.4s: ahí se empieza a ver la página
    var reducido = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setTimeout(terminar, reducido ? 900 : 3400);

    cueva.addEventListener('click', terminar);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') terminar();
    });
})();
