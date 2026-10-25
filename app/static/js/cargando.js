/* Animación de carga (puntos en ola) al pulsar un botón o enlace que lleva a otra página.
 * - Los botones de formularios muestran los puntos dentro del botón (envio_unico.js).
 * - Además, mientras llega la página nueva, aparece una capa con los puntos en el centro.
 * Solo se muestra si la espera pasa de RETRASO_MS: en conexiones rápidas no parpadea.
 */
(function () {
    var RETRASO_MS = 250;
    // Por si la página no cambia (por ejemplo, una descarga): se quita sola
    var MAXIMO_MS = 12000;
    var temporizador = null;
    var limite = null;

    function capa() {
        var el = document.getElementById('capaCargando');
        if (!el) {
            el = document.createElement('div');
            el.id = 'capaCargando';
            el.className = 'capa-cargando';
            el.setAttribute('role', 'status');
            el.setAttribute('aria-live', 'polite');
            el.innerHTML = window.puntosCargando('grande') + '<span class="visually-hidden">Cargando…</span>';
            document.body.appendChild(el);
        }
        return el;
    }

    function mostrar() {
        clearTimeout(temporizador);
        temporizador = setTimeout(function () {
            capa().classList.add('visible');
            clearTimeout(limite);
            limite = setTimeout(ocultar, MAXIMO_MS);
        }, RETRASO_MS);
    }

    function ocultar() {
        clearTimeout(temporizador);
        clearTimeout(limite);
        var el = document.getElementById('capaCargando');
        if (el) el.classList.remove('visible');
    }

    // Puntos en ola; tamaño 'chico' (dentro de un botón) o 'grande' (capa)
    window.puntosCargando = function (tamano) {
        return '<span class="puntos-ola puntos-' + (tamano || 'chico') + '" aria-hidden="true">' +
            '<span></span><span></span><span></span><span></span><span></span></span>';
    };

    function llevaAOtraPagina(enlace, e) {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return false;
        if (enlace.hasAttribute('download') || enlace.hasAttribute('data-bs-toggle')) return false;
        if (enlace.target && enlace.target !== '_self') return false;
        var href = enlace.getAttribute('href');
        if (!href || href.charAt(0) === '#' || /^(javascript|mailto|tel):/i.test(href)) return false;
        var destino = new URL(enlace.href, location.href);
        if (destino.origin !== location.origin) return false;
        if (destino.searchParams.get('descargar') === '1') return false;
        // Mismo lugar, solo cambia el #ancla: no se recarga
        if (destino.pathname === location.pathname && destino.search === location.search && destino.hash) return false;
        return true;
    }

    document.addEventListener('click', function (e) {
        var enlace = e.target.closest && e.target.closest('a[href]');
        if (enlace && llevaAOtraPagina(enlace, e)) mostrar();
    });

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (e.defaultPrevented || form.hasAttribute('data-envio-libre')) return;
        if (form.target && form.target !== '_self') return;
        mostrar();
    });

    // Al volver con "atrás" la página puede venir de la memoria con la capa puesta
    window.addEventListener('pageshow', ocultar);
})();
