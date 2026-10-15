/* Protección CSRF global.
 * - Añade el token a todos los formularios POST (incluso los creados después).
 * - Añade la cabecera X-CSRFToken a cada fetch() del mismo sitio que no sea GET.
 */
(function () {
    function getToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    function ensureToken(form) {
        if (!form || (form.method || '').toLowerCase() !== 'post') return;
        var input = form.querySelector('input[name="csrf_token"]');
        if (!input) {
            input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrf_token';
            form.appendChild(input);
        }
        input.value = getToken();
    }

    // Formularios enviados por el usuario
    document.addEventListener('submit', function (e) { ensureToken(e.target); }, true);

    // Formularios enviados por código con form.submit() (no dispara el evento submit)
    var nativeSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = function () {
        ensureToken(this);
        return nativeSubmit.apply(this, arguments);
    };

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('form').forEach(ensureToken);
    });

    // fetch() hacia el mismo sitio
    if (window.fetch) {
        var nativeFetch = window.fetch;
        window.fetch = function (input, init) {
            init = init || {};
            var method = (init.method || (input && input.method) || 'GET').toUpperCase();
            var url = typeof input === 'string' ? input : (input && input.url) || '';
            var sameOrigin = new URL(url, window.location.href).origin === window.location.origin;
            if (sameOrigin && ['GET', 'HEAD', 'OPTIONS'].indexOf(method) === -1) {
                var headers = new Headers(init.headers || (input && input.headers) || {});
                if (!headers.has('X-CSRFToken')) headers.set('X-CSRFToken', getToken());
                init.headers = headers;
            }
            return nativeFetch.call(this, input, init);
        };
    }
})();
