// Plan mensual de hábitos:
// - En el inicio y en el check, el personaje del login pregunta por el plan del mes.
//   Si se está viendo el saludo de bienvenida, espera a que termine.
// - En la página del plan, un hábito sin marcar apaga sus días.
document.addEventListener('DOMContentLoaded', function () {
    var aviso = document.getElementById('planMesModal');
    if (aviso && window.bootstrap) {
        var abrir = function () { new bootstrap.Modal(aviso).show(); };
        if (document.getElementById('bienvenida')) {
            document.addEventListener('bienvenida:terminada', abrir, { once: true });
        } else {
            abrir();
        }
    }

    document.querySelectorAll('.plan-habito').forEach(function (fila) {
        var check = fila.querySelector('.plan-check');
        var dias = fila.querySelectorAll('.dia-check');
        function actualizar() {
            fila.classList.toggle('excluido', !check.checked);
            dias.forEach(function (d) { d.disabled = !check.checked; });
        }
        check.addEventListener('change', actualizar);
        actualizar();
    });
});
