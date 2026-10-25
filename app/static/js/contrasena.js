// Marca en vivo los requisitos de la contraseña (templates/auth/_requisitos_contrasena.html).
// Son las mismas reglas que REQUISITOS_CONTRASENA en app/models/users.py.
(function () {
    var REGLAS = {
        largo: function (c) { return c.length >= 8; },
        mayuscula: function (c) { return c !== c.toLowerCase(); },
        minuscula: function (c) { return c !== c.toUpperCase(); },
        numero: function (c) { return /\d/.test(c); },
        simbolo: function (c) { return /[^\p{L}\p{N}\s]/u.test(c); }
    };

    document.querySelectorAll('.requisitos-contrasena').forEach(function (lista) {
        var input = document.getElementById(lista.dataset.para);
        if (!input) return;
        var items = lista.querySelectorAll('[data-regla]');

        function revisar() {
            var valor = input.value;
            var todas = true;
            items.forEach(function (li) {
                var cumple = REGLAS[li.dataset.regla](valor);
                todas = todas && cumple;
                li.classList.toggle('cumple', cumple);
                li.querySelector('i').className = cumple ? 'bi bi-check-circle-fill' : 'bi bi-circle';
            });
            input.setCustomValidity(todas ? '' : 'La contraseña no cumple todos los requisitos.');
            return todas;
        }

        input.addEventListener('input', revisar);
        if (input.form) {
            input.form.addEventListener('submit', function (e) {
                if (!revisar()) {
                    e.preventDefault();
                    lista.classList.add('falta');
                    input.focus();
                }
            });
        }
        revisar();
    });
})();
