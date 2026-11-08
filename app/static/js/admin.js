/* Panel de administración: pide confirmación antes de las acciones con data-confirmar
 * (por ejemplo, eliminar un hábito del usuario). */
(function () {
    document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm(form.dataset.confirmar)) e.preventDefault();
        });
    });
})();
