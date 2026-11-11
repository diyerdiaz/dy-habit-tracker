// Muestra la tarjeta con la frase del día una sola vez al día en cada dispositivo.
// Al cerrarla avisa con el evento "frase-dia-cerrada" (el aviso de medallas lo espera).
(function () {
    const CLAVE = 'frase-dia-vista';
    const tarjeta = document.getElementById('fraseDia');
    if (!tarjeta) return;

    const fecha = tarjeta.dataset.fecha;
    let vista;
    try {
        vista = localStorage.getItem(CLAVE);
    } catch (e) {
        // Sin almacenamiento no se puede recordar: mejor no repetirla en cada página
        return;
    }
    if (vista === fecha) return;

    const cerrar = function () {
        if (tarjeta.hidden) return;
        tarjeta.hidden = true;
        document.dispatchEvent(new CustomEvent('frase-dia-cerrada'));
        document.removeEventListener('keydown', alTeclear);
        try {
            localStorage.setItem(CLAVE, fecha);
        } catch (e) { /* no se pudo guardar: volverá a salir */ }
    };

    function alTeclear(evento) {
        if (evento.key === 'Escape') cerrar();
    }

    tarjeta.querySelectorAll('[data-cerrar-frase]').forEach(function (boton) {
        boton.addEventListener('click', cerrar);
    });
    tarjeta.addEventListener('click', function (evento) {
        if (evento.target === tarjeta) cerrar();
    });
    document.addEventListener('keydown', alTeclear);

    tarjeta.hidden = false;
    tarjeta.querySelector('.frase-dia-btn').focus();
})();
