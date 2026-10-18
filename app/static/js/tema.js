// Colores del tema (el del personaje con el que se inició sesión) para usarlos
// desde JavaScript, por ejemplo en las gráficas, que no entienden var(--...).
// Si la página no tiene tema, se usan los morados de siempre.
(function () {
    var POR_DEFECTO = {
        'vivo': '#d966ff', 'grad-1': '#8a28ff', 'grad-2': '#e100ff',
        'vivo-rgb': '217, 102, 255', 'grad-1-rgb': '138, 40, 255', 'grad-2-rgb': '225, 0, 255',
        'fuerte-rgb': '183, 0, 255', 'claro-rgb': '230, 130, 255', 'fondo-rgb': '80, 0, 120',
        'oscuro': '#250035', 'oscuro-2': '#1a002a', 'oscuro-rgb': '30, 0, 45',
    };

    function leer(nombre) {
        var valor = getComputedStyle(document.documentElement).getPropertyValue('--tema-' + nombre).trim();
        return valor || POR_DEFECTO[nombre];
    }

    window.temaColor = function (nombre) {
        return leer(nombre);
    };

    window.temaRgba = function (nombre, alfa) {
        return 'rgba(' + leer(nombre + '-rgb') + ', ' + alfa + ')';
    };
})();
