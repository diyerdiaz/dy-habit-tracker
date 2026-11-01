// Resumen del mes que terminó: sale una sola vez, antes del aviso del plan.
// Si se está viendo el saludo de bienvenida, espera a que termine.
document.addEventListener('DOMContentLoaded', function () {
    var modal = document.getElementById('resumenMesModal');
    if (!modal || !window.bootstrap) return;

    function crearGrafica() {
        var canvas = document.getElementById('resumenMesGrafica');
        if (!canvas || !window.Chart || !window.RESUMEN_MES) return;
        var tema = getComputedStyle(document.documentElement);
        var color = tema.getPropertyValue('--tema-vivo').trim() || '#d966ff';
        var rgb = tema.getPropertyValue('--tema-vivo-rgb').trim() || '217, 102, 255';
        var texto = 'rgba(255, 255, 255, 0.6)';
        var lineas = 'rgba(255, 255, 255, 0.08)';

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: window.RESUMEN_MES.dias,
                datasets: [{
                    label: 'Cumplimiento',
                    data: window.RESUMEN_MES.pct,
                    borderColor: color,
                    backgroundColor: 'rgba(' + rgb + ', 0.15)',
                    borderWidth: 2,
                    fill: true,
                    cubicInterpolationMode: 'monotone',  // la curva no se pasa de 0% ni de 100%
                    spanGaps: true,
                    pointRadius: 2,
                    pointHoverRadius: 5,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function (puntos) { return 'Día ' + puntos[0].label; },
                            label: function (punto) { return punto.parsed.y + '% cumplido'; },
                        },
                    },
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: texto, maxRotation: 0, autoSkipPadding: 10 } },
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: lineas },
                        ticks: { color: texto, stepSize: 25, callback: function (valor) { return valor + '%'; } },
                    },
                },
            },
        });
    }

    modal.addEventListener('shown.bs.modal', function () {
        crearGrafica();
        fetch(modal.dataset.vistoUrl, { method: 'POST' });
    }, { once: true });

    // Avisa al aviso del plan, que sale después
    modal.addEventListener('hidden.bs.modal', function () {
        document.dispatchEvent(new Event('resumen:cerrado'));
    }, { once: true });

    var abrir = function () { new bootstrap.Modal(modal).show(); };
    if (document.getElementById('bienvenida')) {
        document.addEventListener('bienvenida:terminada', abrir, { once: true });
    } else {
        abrir();
    }
});
