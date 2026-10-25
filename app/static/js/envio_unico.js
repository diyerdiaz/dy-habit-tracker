/* Evita enviar dos veces el mismo formulario.
 * Si el servidor tarda y se vuelve a pulsar "Guardar", el segundo clic se ignora
 * y el botón muestra que ya se está guardando.
 */
(function () {
    document.addEventListener('submit', function (e) {
        var form = e.target;
        // Otro script canceló el envío (por ejemplo, una validación): no se bloquea
        if (e.defaultPrevented || form.hasAttribute('data-envio-libre')) return;

        if (form.dataset.enviando === '1') {
            e.preventDefault();
            return;
        }
        form.dataset.enviando = '1';
        form.querySelectorAll('button[type="submit"], button:not([type]), input[type="submit"]').forEach(function (boton) {
            boton.classList.add('enviando');
            boton.setAttribute('aria-disabled', 'true');
            if (boton.tagName === 'BUTTON') {
                boton.dataset.textoOriginal = boton.innerHTML;
                boton.innerHTML = window.puntosCargando('chico') + '<span class="visually-hidden">Procesando…</span>';
            }
        });
    });

    // Al volver con el botón "atrás" el navegador puede mostrar la página guardada en memoria
    window.addEventListener('pageshow', function () {
        document.querySelectorAll('form[data-enviando="1"]').forEach(function (form) {
            delete form.dataset.enviando;
            form.querySelectorAll('.enviando').forEach(function (boton) {
                boton.classList.remove('enviando');
                boton.removeAttribute('aria-disabled');
                if (boton.dataset.textoOriginal !== undefined) boton.innerHTML = boton.dataset.textoOriginal;
            });
        });
    });
})();
