/* Mis Retos: al aceptar un reto aparece una pantalla en la que el texto se
 * escribe solo, letra por letra; al terminar se envía el formulario. */
(function () {
    var pantalla = document.getElementById('retoInicio');
    if (!pantalla) return;
    var linea1 = document.getElementById('retoInicioLinea1');
    var linea2 = document.getElementById('retoInicioLinea2');
    // Una al azar cada vez que se acepta un reto
    var FRASES = [
        'Las excusas no ganan retos. Tú sí.',
        'Hoy le declaras la guerra a tu peor versión.',
        'Nadie te va a obligar. Por eso vale tanto.',
        'El dolor de la disciplina pesa menos que el del arrepentimiento.',
        'Tu palabra contra tus excusas. Que gane tu palabra.',
        'Los que cumplen no son más fuertes: solo no se rinden.',
        'Mañana vas a agradecer lo que empiezas hoy.',
    ];
    // Reto "todo o nada": se apostó todo el XP
    var FRASES_TODO = [
        'Lo apostaste todo. Ahora no hay vuelta atrás.',
        'Todo o nada. Y tú no viniste por la nada.',
    ];
    var MS_POR_LETRA = 45;
    var PAUSA_FINAL_MS = 900;
    var sinMovimiento = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function escribir(el, texto, listo) {
        var i = 0;
        el.textContent = '';
        el.classList.add('escribiendo');
        (function siguiente() {
            el.textContent = texto.slice(0, ++i);
            if (i < texto.length) {
                setTimeout(siguiente, MS_POR_LETRA);
            } else {
                el.classList.remove('escribiendo');
                listo();
            }
        })();
    }

    document.querySelectorAll('form[data-iniciar-reto]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (form.dataset.iniciando === '1') return;
            e.preventDefault();
            form.dataset.iniciando = '1';
            var titulo = 'Iniciando «' + form.dataset.iniciarReto + '»…';
            var opciones = form.hasAttribute('data-todo-xp') ? FRASES_TODO : FRASES;
            var FRASE = opciones[Math.floor(Math.random() * opciones.length)];
            pantalla.hidden = false;
            if (sinMovimiento) {
                linea1.textContent = titulo;
                linea2.textContent = FRASE;
                setTimeout(function () { form.submit(); }, PAUSA_FINAL_MS);
                return;
            }
            escribir(linea1, titulo, function () {
                escribir(linea2, FRASE, function () {
                    setTimeout(function () { form.submit(); }, PAUSA_FINAL_MS);
                });
            });
        });
    });

    // Al volver con "atrás" la página puede venir de la memoria con la pantalla puesta
    window.addEventListener('pageshow', function () {
        pantalla.hidden = true;
        document.querySelectorAll('form[data-iniciando]').forEach(function (f) { delete f.dataset.iniciando; });
    });
})();
