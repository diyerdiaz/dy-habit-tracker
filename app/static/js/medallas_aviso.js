/* Aviso obligatorio "¡Ganaste una medalla!" en cualquier pantalla, una medalla
 * a la vez. Solo se cierra con su botón (ni Escape ni tocando fuera): hasta
 * aceptarlo, vuelve a salir al recargar. Al aceptarlo se guarda en la base de
 * datos y esa medalla no se anuncia nunca más, aunque la app se actualice.
 * Revisa al cargar la página y después de cada acción hecha con fetch (marcar
 * un hábito, completar una tarea...). Si está abierta la frase del día, espera
 * a que se cierre: primero la frase, después las medallas. */
(function () {
    var aviso = document.getElementById('medallaAviso');
    if (!aviso) return;
    var tarjeta = aviso.querySelector('.medalla-aviso');
    var boton = document.getElementById('medallaAvisoOk');
    var urlSinVer = aviso.dataset.urlSinVer;
    var urlVista = aviso.dataset.urlVista;
    var fetchOriginal = window.fetch.bind(window);
    var cola = [];
    var enCola = {};
    var actual = null;
    var frase = document.getElementById('fraseDia');
    var RAREZAS = { bronce: 'Bronce', plata: 'Plata', oro: 'Oro', diamante: 'Diamante', mitica: 'Mítica' };

    function texto(id, valor) {
        document.getElementById(id).textContent = valor;
    }

    function fraseAbierta() {
        return frase && !frase.hidden;
    }

    function mostrarSiguiente() {
        if (actual || fraseAbierta()) return;
        if (!cola.length) {
            aviso.hidden = true;
            document.body.classList.remove('medalla-aviso-abierto');
            return;
        }
        actual = cola.shift();
        tarjeta.className = 'medalla-aviso rareza-' + actual.rareza;
        document.getElementById('medallaAvisoIcono').className = 'bi ' + actual.icono;
        texto('medallaAvisoRareza', RAREZAS[actual.rareza] || actual.rareza);
        texto('medallaAvisoNombre', actual.nombre);
        texto('medallaAvisoDescripcion', actual.descripcion);
        texto('medallaAvisoFrase', '“' + actual.frase + '”');
        var quedan = document.getElementById('medallaAvisoQuedan');
        quedan.hidden = cola.length === 0;
        quedan.textContent = cola.length === 1 ? 'Tienes 1 medalla más por ver' : 'Tienes ' + cola.length + ' medallas más por ver';
        boton.textContent = cola.length ? 'Siguiente' : '¡Genial!';
        boton.disabled = false;
        aviso.hidden = false;
        document.body.classList.add('medalla-aviso-abierto');
        boton.focus();
    }

    // Solo se pasa a la siguiente cuando el servidor guardó que esta ya se vio;
    // si falla (sin conexión), el aviso se queda para volver a intentarlo.
    function aceptar() {
        if (!actual) return;
        boton.disabled = true;
        fetchOriginal(urlVista.replace('__ID__', encodeURIComponent(actual.id)), { method: 'POST' })
            .then(function (r) {
                if (!r.ok && r.status !== 404) throw new Error('no guardado');
                actual = null;
                mostrarSiguiente();
            })
            .catch(function () { boton.disabled = false; });
    }

    function revisar() {
        fetchOriginal(urlSinVer, { headers: { Accept: 'application/json' } })
            .then(function (r) { return r.ok ? r.json() : []; })
            .then(function (medallas) {
                medallas.forEach(function (m) {
                    if (!enCola[m.id]) {
                        enCola[m.id] = true;
                        cola.push(m);
                    }
                });
                if (actual) {
                    // Se actualiza el contador de las que faltan
                    var quedan = document.getElementById('medallaAvisoQuedan');
                    quedan.hidden = cola.length === 0;
                    quedan.textContent = cola.length === 1 ? 'Tienes 1 medalla más por ver' : 'Tienes ' + cola.length + ' medallas más por ver';
                    boton.textContent = cola.length ? 'Siguiente' : '¡Genial!';
                } else {
                    mostrarSiguiente();
                }
            })
            .catch(function () {});
    }

    boton.addEventListener('click', aceptar);
    document.addEventListener('frase-dia-cerrada', mostrarSiguiente);
    // Obligatorio: Escape no lo cierra y el foco no sale del aviso
    document.addEventListener('keydown', function (e) {
        if (aviso.hidden) return;
        if (e.key === 'Escape') e.preventDefault();
        if (e.key === 'Tab') {
            e.preventDefault();
            boton.focus();
        }
    });

    // Después de cualquier acción que cambia algo (POST, PUT...) se vuelve a revisar
    window.fetch = function (recurso, opciones) {
        var promesa = fetchOriginal(recurso, opciones);
        var metodo = ((opciones && opciones.method) || (recurso && recurso.method) || 'GET').toUpperCase();
        if (metodo !== 'GET') {
            promesa.then(function () { revisar(); }, function () {});
        }
        return promesa;
    };

    revisar();
})();
