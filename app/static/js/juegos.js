// Juegos de vocabulario. "Unir parejas": se toca una palabra en inglés y luego su
// significado (o al revés). Todas las palabras llegan con la página, así que las
// rondas se arman aquí sin pedir nada al servidor; solo se envía el resultado.

document.addEventListener('DOMContentLoaded', () => {
    const juego = document.getElementById('juegoUnir');
    if (!juego) return;

    const palabras = JSON.parse(document.getElementById('unirPalabras').textContent);
    const porRonda = Number(juego.dataset.porRonda);
    const listaIngles = document.getElementById('unirIngles');
    const listaEspanol = document.getElementById('unirEspanol');
    const tablero = document.getElementById('unirTablero');
    const final = document.getElementById('unirFinal');
    const $ = (id) => document.getElementById(id);

    let ronda = [];            // palabras de la ronda actual
    let anteriores = new Set(); // ids de la ronda pasada, para no repetirlas enseguida al rellenar la bolsa
    let elegido = null;        // botón tocado esperando su pareja
    let aciertos = 0;
    let errores = 0;
    let inicio = 0;
    let reloj = null;
    let bloqueado = false;     // mientras se anima un error no se aceptan toques

    // ── Sonido: pronunciar la palabra al acertar (se recuerda la preferencia) ──
    const botonSonido = $('unirSonido');
    let sonido = 'speechSynthesis' in window;
    try { if (localStorage.getItem('juegosSonido') === 'no') sonido = false; } catch (e) { /* sin almacenamiento */ }
    function pintarSonido() {
        botonSonido.setAttribute('aria-pressed', String(sonido));
        botonSonido.querySelector('i').className = sonido ? 'bi bi-volume-up-fill' : 'bi bi-volume-mute-fill';
    }
    if (!('speechSynthesis' in window)) botonSonido.hidden = true;
    botonSonido.addEventListener('click', () => {
        sonido = !sonido;
        try { localStorage.setItem('juegosSonido', sonido ? 'si' : 'no'); } catch (e) { /* sin almacenamiento */ }
        pintarSonido();
    });
    pintarSonido();

    function pronunciar(texto) {
        if (!sonido) return;
        const voz = new SpeechSynthesisUtterance(texto);
        voz.lang = 'en-US';
        voz.rate = 0.9;
        speechSynthesis.cancel();
        speechSynthesis.speak(voz);
    }

    // ── Armar la ronda ──
    const normalizar = (texto) => texto.trim().toLowerCase();

    // Bolsa de palabras: salen al azar y ninguna se repite hasta que hayan salido
    // todas; entonces se vuelve a llenar. Se guarda en el navegador, así que
    // también se respeta al recargar la página o volver otro día.
    const CLAVE_BOLSA = 'juegosUnirPendientes';
    const porId = new Map(palabras.map((p) => [p.id, p]));

    function leerBolsa() {
        try {
            const guardada = JSON.parse(localStorage.getItem(CLAVE_BOLSA) || '[]');
            return Array.isArray(guardada) ? guardada.filter((id) => porId.has(id)) : [];
        } catch (e) {
            return [];
        }
    }

    function guardarBolsa(bolsa) {
        try { localStorage.setItem(CLAVE_BOLSA, JSON.stringify(bolsa)); } catch (e) { /* sin almacenamiento */ }
    }

    function elegirPalabras() {
        const cantidad = Math.min(porRonda, palabras.length);
        const elegidas = [];
        const vistos = new Set();   // dos palabras con el mismo significado no pueden ir juntas
        const cabe = (p) => {
            const claves = ['en:' + normalizar(p.en), 'es:' + normalizar(p.es)];
            if (claves.some((c) => vistos.has(c))) return false;
            claves.forEach((c) => vistos.add(c));
            return true;
        };
        const tomarDe = (bolsa) => {
            for (let i = 0; i < bolsa.length && elegidas.length < cantidad; ) {
                const p = porId.get(bolsa[i]);
                if (!elegidas.includes(p) && cabe(p)) {
                    elegidas.push(p);
                    bolsa.splice(i, 1);
                } else {
                    i++;
                }
            }
        };

        let bolsa = leerBolsa();
        tomarDe(bolsa);
        if (elegidas.length < cantidad) {
            // Ya salieron todas: bolsa nueva, dejando al final las de la ronda pasada
            // para que no vuelvan a salir enseguida
            const resto = mezclar(palabras.map((p) => p.id).filter((id) => !elegidas.some((p) => p.id === id)));
            bolsa = resto.filter((id) => !anteriores.has(id)).concat(resto.filter((id) => anteriores.has(id)));
            tomarDe(bolsa);
        }
        guardarBolsa(bolsa);
        return elegidas;
    }

    function mezclar(lista) {
        const copia = lista.slice();
        for (let i = copia.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [copia[i], copia[j]] = [copia[j], copia[i]];
        }
        return copia;
    }

    // Que ninguna pareja quede en la misma fila: sería demasiado fácil
    function mezclarSinCoincidir(lista, otra) {
        let mejor = mezclar(lista);
        for (let intento = 0; intento < 20 && lista.length > 1; intento++) {
            if (mejor.every((p, i) => p !== otra[i])) break;
            mejor = mezclar(lista);
        }
        return mejor;
    }

    function crearBoton(palabra, lado) {
        const boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'unir-ficha';
        boton.dataset.lado = lado;
        boton.dataset.id = palabra.id;
        boton.textContent = lado === 'en' ? palabra.en : palabra.es;
        boton.lang = lado === 'en' ? 'en' : 'es';
        return boton;
    }

    function nuevaRonda() {
        ronda = elegirPalabras();
        anteriores = new Set(ronda.map((p) => p.id));
        aciertos = 0;
        errores = 0;
        elegido = null;
        bloqueado = false;

        const izquierda = mezclar(ronda);
        const derecha = mezclarSinCoincidir(ronda, izquierda);
        listaIngles.replaceChildren(...izquierda.map((p) => crearBoton(p, 'en')));
        listaEspanol.replaceChildren(...derecha.map((p) => crearBoton(p, 'es')));

        $('unirTotal').textContent = ronda.length;
        actualizarBarra();
        final.hidden = true;
        tablero.hidden = false;

        inicio = Date.now();
        clearInterval(reloj);
        reloj = setInterval(() => { $('unirTiempo').textContent = formatoTiempo(segundos()); }, 1000);
        $('unirTiempo').textContent = '0:00';
    }

    const segundos = () => Math.round((Date.now() - inicio) / 1000);
    const formatoTiempo = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

    function actualizarBarra() {
        $('unirAciertos').textContent = aciertos;
        $('unirErrores').textContent = errores;
    }

    // ── Jugar ──
    const palabraDe = (boton) => ronda.find((p) => String(p.id) === boton.dataset.id);

    // Compara por texto, no por id: si dos palabras comparten significado, ambas valen
    function sonPareja(a, b) {
        const en = palabraDe(a.dataset.lado === 'en' ? a : b);
        const es = palabraDe(a.dataset.lado === 'es' ? a : b);
        return normalizar(en.es) === normalizar(es.es) || normalizar(en.en) === normalizar(es.en);
    }

    tablero.addEventListener('click', (e) => {
        const boton = e.target.closest('.unir-ficha');
        if (!boton || bloqueado || boton.classList.contains('acertada')) return;

        if (!elegido) {
            elegido = boton;
            boton.classList.add('elegida');
            return;
        }
        if (elegido === boton) {            // tocar la misma ficha la suelta
            boton.classList.remove('elegida');
            elegido = null;
            return;
        }
        if (elegido.dataset.lado === boton.dataset.lado) {  // cambia de opción en la misma columna
            elegido.classList.remove('elegida');
            elegido = boton;
            boton.classList.add('elegida');
            return;
        }

        const primero = elegido;
        elegido = null;
        primero.classList.remove('elegida');

        if (sonPareja(primero, boton)) {
            [primero, boton].forEach((b) => { b.classList.add('acertada'); b.disabled = true; });
            aciertos++;
            const ingles = primero.dataset.lado === 'en' ? primero : boton;
            pronunciar(ingles.textContent);
            actualizarBarra();
            if (aciertos === ronda.length) setTimeout(terminar, 450);
        } else {
            errores++;
            actualizarBarra();
            bloqueado = true;
            [primero, boton].forEach((b) => b.classList.add('fallida'));
            setTimeout(() => {
                [primero, boton].forEach((b) => b.classList.remove('fallida'));
                bloqueado = false;
            }, 600);
        }
    });

    // ── Fin de la ronda ──
    function terminar() {
        clearInterval(reloj);
        const tiempo = segundos();
        const precision = Math.round(ronda.length / (ronda.length + errores) * 100);

        $('unirFinalIcono').textContent = errores === 0 ? '🏆' : precision >= 70 ? '🎉' : '💪';
        $('unirFinalTitulo').textContent = errores === 0 ? '¡Ronda perfecta!' : precision >= 70 ? '¡Muy bien!' : '¡Ronda completa, sigue practicando!';
        $('unirFinalTiempo').textContent = formatoTiempo(tiempo);
        $('unirFinalErrores').textContent = errores;
        $('unirFinalPrecision').textContent = `${precision}%`;
        const nota = $('unirFinalNota');
        nota.innerHTML = window.puntosCargando ? window.puntosCargando('chico') + ' Guardando…' : 'Guardando…';

        tablero.hidden = true;
        final.hidden = false;
        $('unirOtra').focus();

        fetch(juego.dataset.resultadoUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: ronda.map((p) => p.id), errores, segundos: tiempo }),
        })
            .then((res) => res.json())
            .then((data) => {
                if (!data.success) throw new Error();
                nota.textContent = 'Ronda guardada en tus estadísticas.';
            })
            .catch(() => {
                nota.textContent = 'No se pudo guardar la ronda (¿sin internet?). Puedes seguir jugando.';
            });
    }

    $('unirOtra').addEventListener('click', nuevaRonda);

    nuevaRonda();
});
