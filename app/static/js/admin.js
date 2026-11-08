/* Panel de administración: pide confirmación antes de las acciones con data-confirmar
 * (por ejemplo, eliminar un hábito del usuario). */
(function () {
    document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm(form.dataset.confirmar)) e.preventDefault();
        });
    });
})();

/* Reto con "Todo su XP": la cantidad no se usa, así que se desactiva */
(function () {
    var cantidad = document.getElementById('apuestaCantidad');
    if (!cantidad) return;
    document.querySelectorAll('input[name="modo_apuesta"]').forEach(function (radio) {
        radio.addEventListener('change', function () {
            cantidad.disabled = radio.value === 'todo' && radio.checked;
        });
    });
})();

/* Reto: "Termina" no puede ser antes de "Empieza" (el servidor también lo revisa) */
(function () {
    var inicio = document.getElementById('retoInicio');
    var fin = document.getElementById('retoFin');
    if (!inicio || !fin) return;
    function ajustar() {
        if (!inicio.value) return;
        fin.min = inicio.value;
        if (fin.value && fin.value < inicio.value) fin.value = inicio.value;
    }
    inicio.addEventListener('change', ajustar);
    ajustar();
})();
