// Gráficas de rendimiento del dashboard de Inglés (líneas): día a día, mes a mes y año a año.
// Los datos vienen del servidor en <script id="inglesGraficasDatos">.
(function () {
    const nodoDatos = document.getElementById('inglesGraficasDatos');
    if (!nodoDatos || typeof Chart === 'undefined') return;
    const datos = JSON.parse(nodoDatos.textContent);

    // Paleta validada para fondo oscuro (cada serie siempre con el mismo color)
    const COLORES = { palabras: '#3987e5', repasos: '#d95926', partidas: '#199e70', minutos: '#9085e9' };
    const SUBTITULOS = { dia: 'Últimos 30 días', mes: 'Últimos 12 meses', anio: 'Año por año' };
    const TEXTO = '#c3c2b7';
    const REJILLA = 'rgba(255, 255, 255, 0.07)';
    // En el celular se muestran menos fechas abajo para que no se amontonen
    const ETIQUETAS_X = window.innerWidth < 576 ? 4 : 8;

    const linea = (etiqueta, color) => ({
        label: etiqueta,
        data: [],
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        // 'monotone': curva suave que nunca pasa por encima ni por debajo de los valores reales
        cubicInterpolationMode: 'monotone',
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBorderWidth: 2,
        pointHoverBorderColor: '#020b18',
    });

    const opciones = (unidad, conLeyenda) => ({
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { right: 8, top: 4 } },
        // Al pasar el mouse se ven todas las series de ese día/mes/año juntas
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: {
                display: conLeyenda,
                position: 'top',
                align: 'start',
                labels: { color: TEXTO, usePointStyle: true, pointStyle: 'line', boxWidth: 24 },
            },
            tooltip: {
                backgroundColor: 'rgba(2, 11, 24, 0.95)',
                borderColor: 'rgba(77, 171, 255, 0.4)',
                borderWidth: 1,
                titleColor: '#fff',
                bodyColor: TEXTO,
                padding: 10,
                callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y}${unidad}` },
            },
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { color: TEXTO, maxRotation: 0, autoSkip: true, maxTicksLimit: ETIQUETAS_X },
            },
            y: {
                beginAtZero: true,
                grid: { color: REJILLA },
                border: { display: false },
                ticks: { color: TEXTO, precision: 0, maxTicksLimit: 5 },
            },
        },
    });

    const actividad = new Chart(document.getElementById('graficaActividad'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                linea('Palabras agregadas', COLORES.palabras),
                linea('Repasos', COLORES.repasos),
                linea('Partidas', COLORES.partidas),
            ],
        },
        options: opciones('', true),
    });

    // Español no tiene shadowing: esa gráfica solo existe en Inglés
    const lienzoShadowing = document.getElementById('graficaShadowing');
    const shadowing = lienzoShadowing ? new Chart(lienzoShadowing, {
        type: 'line',
        data: { labels: [], datasets: [linea('Shadowing', COLORES.minutos)] },
        options: opciones(' min', false),
    }) : null;

    function mostrar(periodo) {
        const d = datos[periodo];
        // Con pocos puntos (año a año) se marcan para que se vean
        const radio = d.etiquetas.length <= 12 ? 4 : 0;

        actividad.data.labels = d.etiquetas;
        actividad.data.datasets[0].data = d.palabras;
        actividad.data.datasets[1].data = d.repasos;
        actividad.data.datasets[2].data = d.partidas;
        actividad.data.datasets.forEach((s) => { s.pointRadius = radio; });
        actividad.update();

        if (shadowing) {
            shadowing.data.labels = d.etiquetas;
            shadowing.data.datasets[0].data = d.minutos;
            shadowing.data.datasets[0].pointRadius = radio;
            shadowing.update();
        }

        document.querySelectorAll('[data-subtitulo]').forEach((p) => { p.textContent = SUBTITULOS[periodo]; });
        document.querySelectorAll('.ingles-periodo').forEach((b) => {
            const activo = b.dataset.periodo === periodo;
            b.classList.toggle('activo', activo);
            b.setAttribute('aria-selected', activo ? 'true' : 'false');
        });
    }

    document.querySelectorAll('.ingles-periodo').forEach((b) => {
        b.addEventListener('click', () => mostrar(b.dataset.periodo));
    });
    mostrar('dia');
})();
