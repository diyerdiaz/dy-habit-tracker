/* Avisos (flash): se cierran solos para no estorbar. Los de éxito o
 * información duran menos que las advertencias y los errores. Al cerrarse,
 * su espacio se encoge y, cuando no queda ninguno, se quita el contenedor
 * (en el celular deja un margen para no quedar debajo del menú). */
(function () {
    var contenedor = document.getElementById('avisos');
    if (!contenedor) return;
    var MS_NORMAL = 4500;
    var MS_IMPORTANTE = 8000;
    var MS_ANIMACION = 450;

    function quitarContenedorSiVacio() {
        if (!contenedor.querySelector('.flash-message')) contenedor.remove();
    }

    function cerrar(aviso) {
        if (!aviso.isConnected || aviso.classList.contains('saliendo')) return;
        // Se fija su altura actual para que el encogimiento sea animado
        aviso.style.maxHeight = aviso.offsetHeight + 'px';
        void aviso.offsetHeight;
        aviso.classList.add('saliendo');
        setTimeout(function () {
            aviso.remove();
            quitarContenedorSiVacio();
        }, MS_ANIMACION);
    }

    contenedor.querySelectorAll('.flash-message').forEach(function (aviso) {
        var importante = aviso.classList.contains('alert-danger') || aviso.classList.contains('alert-warning');
        var temporizador = setTimeout(function () { cerrar(aviso); }, importante ? MS_IMPORTANTE : MS_NORMAL);
        // Mientras se toca o se pasa el mouse por encima, no se cierra
        ['mouseenter', 'touchstart'].forEach(function (evento) {
            aviso.addEventListener(evento, function () { clearTimeout(temporizador); }, { passive: true });
        });
        // La ✕ también lo cierra con la misma animación
        var boton = aviso.querySelector('.btn-close');
        if (boton) {
            boton.removeAttribute('data-bs-dismiss');
            boton.addEventListener('click', function () {
                clearTimeout(temporizador);
                cerrar(aviso);
            });
        }
    });
})();
