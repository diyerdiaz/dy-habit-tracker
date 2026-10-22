// Estadísticas de hábitos: pestañas "Comparar meses" y "Calendario".

// ── Calendario: al tocar un día se muestra su detalle debajo ──
(function () {
    var dias = document.querySelectorAll('.cal-dia[data-dia]');
    if (!dias.length) return;
    var vacio = document.getElementById('calDetalleVacio');

    function elegir(boton) {
        dias.forEach(function (d) { d.classList.toggle('elegido', d === boton); });
        document.querySelectorAll('.cal-detalle-dia').forEach(function (el) { el.hidden = true; });
        var detalle = document.getElementById('dia-' + boton.dataset.dia);
        if (detalle) detalle.hidden = false;
        vacio.hidden = true;
    }

    dias.forEach(function (boton) {
        boton.addEventListener('click', function () {
            elegir(boton);
            if (window.innerWidth < 768) {
                document.getElementById('calDetalle').scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Al abrir, muestra el día de hoy si está en este mes
    var hoy = document.querySelector('.cal-dia.hoy');
    if (hoy) elegir(hoy);
})();

// ── Comparar: no dejar marcar más meses del máximo ──
(function () {
    var casillas = document.querySelectorAll('.cmp-meses input[type="checkbox"]');
    if (!casillas.length) return;
    var ayuda = document.getElementById('cmpAyuda');
    var maximo = parseInt(ayuda.dataset.max, 10);

    function revisar() {
        var marcadas = Array.prototype.filter.call(casillas, function (c) { return c.checked; }).length;
        casillas.forEach(function (c) { c.disabled = !c.checked && marcadas >= maximo; });
        ayuda.classList.toggle('al-limite', marcadas >= maximo);
    }

    casillas.forEach(function (c) { c.addEventListener('change', revisar); });
    revisar();
})();
