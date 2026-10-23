// Saludo al entrar: se muestra un momento y se desvanece.
// Sale al iniciar sesión y cada vez que se abre la página de nuevo (pestaña o app nueva),
// pero no al volver al inicio dentro de la misma visita. Se cierra antes con un toque o Esc.
(function () {
    var bienvenida = document.getElementById('bienvenida');
    if (!bienvenida) return;

    var CLAVE = 'bienvenidaVista';
    var vista = false;
    try { vista = sessionStorage.getItem(CLAVE) === '1'; } catch (e) {}
    // Este script corre justo después del saludo, así que se quita antes de pintarse
    if (vista && bienvenida.dataset.login !== '1') {
        bienvenida.remove();
        return;
    }
    try { sessionStorage.setItem(CLAVE, '1'); } catch (e) {}

    var terminada = false;
    function terminar() {
        if (terminada) return;
        terminada = true;
        bienvenida.classList.add('is-saliendo');
        setTimeout(function () { bienvenida.remove(); }, 550);
        // Avisa a otras partes de la página (p. ej. el aviso del plan del mes)
        document.dispatchEvent(new Event('bienvenida:terminada'));
    }

    setTimeout(terminar, 1800);
    bienvenida.addEventListener('click', terminar);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') terminar();
    });
})();
