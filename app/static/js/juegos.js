// Juegos de vocabulario. Todas las palabras llegan con la página, así que las
// rondas se arman aquí sin pedir nada al servidor; solo se envía el resultado.
//  - Unir parejas: se toca una palabra en inglés y luego su significado (o al revés).
//  - Sopa de letras: los significados son las pistas; se toca la primera y la
//    última letra de la palabra en inglés dentro de la cuadrícula.
//  - Ahorcado: se adivina la palabra letra por letra; la pista es un ejemplo en
//    inglés con la palabra tapada y el significado solo se ve al terminarla.
//  - Caza de patos: sale un significado y hay que dispararle al pato que lleva
//    su palabra en inglés antes de que cruce la pantalla.
//  - Crucigrama: los significados son las pistas y las palabras en inglés se
//    cruzan en una cuadrícula que se arma aquí con las palabras de la ronda.
//  - Carrera del mono: para saltar cada obstáculo se elige la palabra que completa
//    un ejemplo en inglés; al tropezar se enseña la frase completa con su significado.

const $ = (id) => document.getElementById(id);
const normalizar = (texto) => texto.trim().toLowerCase();
const formatoTiempo = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
const azar = (n) => Math.floor(Math.random() * n);

function mezclar(lista) {
    const copia = lista.slice();
    for (let i = copia.length - 1; i > 0; i--) {
        const j = azar(i + 1);
        [copia[i], copia[j]] = [copia[j], copia[i]];
    }
    return copia;
}

function leerPreferencia(clave) {
    try { return localStorage.getItem(clave); } catch (e) { return null; }
}

function guardarPreferencia(clave, valor) {
    try { localStorage.setItem(clave, valor); } catch (e) { /* sin almacenamiento */ }
}

// ── Sonido: pronunciar la palabra al acertar (se recuerda la preferencia) ──
function crearSonido(boton) {
    let activo = 'speechSynthesis' in window && leerPreferencia('juegosSonido') !== 'no';
    const pintar = () => {
        boton.setAttribute('aria-pressed', String(activo));
        boton.querySelector('i').className = activo ? 'bi bi-volume-up-fill' : 'bi bi-volume-mute-fill';
    };
    if (!('speechSynthesis' in window)) boton.hidden = true;
    boton.addEventListener('click', () => {
        activo = !activo;
        guardarPreferencia('juegosSonido', activo ? 'si' : 'no');
        pintar();
    });
    pintar();
    return function pronunciar(texto) {
        if (!activo) return;
        const voz = new SpeechSynthesisUtterance(texto);
        voz.lang = 'en-US';
        voz.rate = 0.9;
        speechSynthesis.cancel();
        speechSynthesis.speak(voz);
    };
}

// ── Bolsa de palabras: salen al azar y ninguna se repite hasta que hayan salido
// todas; entonces se vuelve a llenar. Se guarda en el navegador, así que también
// se respeta al recargar la página o volver otro día. ──
function crearBolsa(clave, palabras) {
    const porId = new Map(palabras.map((p) => [p.id, p]));
    let anteriores = new Set(); // ids de la ronda pasada, para no repetirlas enseguida al rellenar la bolsa

    function leer() {
        try {
            const guardada = JSON.parse(localStorage.getItem(clave) || '[]');
            return Array.isArray(guardada) ? guardada.filter((id) => porId.has(id)) : [];
        } catch (e) {
            return [];
        }
    }
    const guardar = (bolsa) => guardarPreferencia(clave, JSON.stringify(bolsa));

    return {
        // `clavesDe(p)` da lo que no puede repetirse dentro de una ronda (por ejemplo
        // el significado); `sirve(p)` deja fuera palabras que esta ronda no admite.
        sacar(cantidad, clavesDe, sirve = () => true) {
            const elegidas = [];
            const vistas = new Set();
            const cabe = (p) => {
                const claves = clavesDe(p);
                if (!sirve(p) || claves.some((c) => vistas.has(c))) return false;
                claves.forEach((c) => vistas.add(c));
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

            let bolsa = leer();
            tomarDe(bolsa);
            if (elegidas.length < cantidad) {
                // Ya salieron todas: bolsa nueva, dejando al final las de la ronda pasada
                // para que no vuelvan a salir enseguida
                const resto = mezclar(palabras.map((p) => p.id).filter((id) => !elegidas.some((p) => p.id === id)));
                bolsa = resto.filter((id) => !anteriores.has(id)).concat(resto.filter((id) => anteriores.has(id)));
                tomarDe(bolsa);
            }
            guardar(bolsa);
            anteriores = new Set(elegidas.map((p) => p.id));
            return elegidas;
        },
        // Palabras que se sacaron pero no se jugaron: vuelven al frente de la bolsa
        devolver(ids) {
            guardar(ids.concat(leer().filter((id) => !ids.includes(id))));
        },
    };
}

function crearReloj(elemento) {
    let inicio = 0;
    let intervalo = null;
    const segundos = () => Math.round((Date.now() - inicio) / 1000);
    return {
        empezar() {
            inicio = Date.now();
            clearInterval(intervalo);
            elemento.textContent = '0:00';
            intervalo = setInterval(() => { elemento.textContent = formatoTiempo(segundos()); }, 1000);
        },
        parar() {
            clearInterval(intervalo);
            return segundos();
        },
    };
}

function guardarResultado(url, datos, nota) {
    nota.innerHTML = window.puntosCargando ? window.puntosCargando('chico') + ' Guardando…' : 'Guardando…';
    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos),
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

// ═══════════════════════════ Unir parejas ═══════════════════════════

function iniciarUnir(juego) {
    const palabras = JSON.parse($('unirPalabras').textContent);
    const porRonda = Number(juego.dataset.porRonda);
    const listaIngles = $('unirIngles');
    const listaEspanol = $('unirEspanol');
    const tablero = $('unirTablero');
    const final = $('unirFinal');
    const pronunciar = crearSonido($('unirSonido'));
    const bolsa = crearBolsa('juegosUnirPendientes', palabras);
    const reloj = crearReloj($('unirTiempo'));
    // Dos palabras con el mismo significado (o la misma palabra) no pueden ir juntas
    const clavesUnir = (p) => ['en:' + normalizar(p.en), 'es:' + normalizar(p.es)];

    let ronda = [];            // palabras de la ronda actual
    let elegido = null;        // botón tocado esperando su pareja
    let aciertos = 0;
    let errores = 0;
    let bloqueado = false;     // mientras se anima un error no se aceptan toques

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
        ronda = bolsa.sacar(Math.min(porRonda, palabras.length), clavesUnir);
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
        reloj.empezar();
    }

    function actualizarBarra() {
        $('unirAciertos').textContent = aciertos;
        $('unirErrores').textContent = errores;
    }

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

    function terminar() {
        const tiempo = reloj.parar();
        const precision = Math.round(ronda.length / (ronda.length + errores) * 100);

        $('unirFinalIcono').textContent = errores === 0 ? '🏆' : precision >= 70 ? '🎉' : '💪';
        $('unirFinalTitulo').textContent = errores === 0 ? '¡Ronda perfecta!' : precision >= 70 ? '¡Muy bien!' : '¡Ronda completa, sigue practicando!';
        $('unirFinalTiempo').textContent = formatoTiempo(tiempo);
        $('unirFinalErrores').textContent = errores;
        $('unirFinalPrecision').textContent = `${precision}%`;

        tablero.hidden = true;
        final.hidden = false;
        $('unirOtra').focus();
        guardarResultado(juego.dataset.resultadoUrl,
            { ids: ronda.map((p) => p.id), errores, segundos: tiempo }, $('unirFinalNota'));
    }

    $('unirOtra').addEventListener('click', nuevaRonda);
    nuevaRonda();
}

// ═══════════════════════════ Sopa de letras ═══════════════════════════

// Direcciones como [fila, columna]: → ↓ ↘ ↗ y sus contrarias
const DIRECCIONES = {
    facil: [[0, 1], [1, 0]],
    normal: [[0, 1], [1, 0], [1, 1], [-1, 1]],
    dificil: [[0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [-1, -1], [1, -1]],
};
const TODAS_LAS_DIRECCIONES = DIRECCIONES.dificil;
const ABECEDARIO = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const COLORES_SOPA = ['#4dabff', '#00e676', '#ffb347', '#ff6fb5', '#b388ff', '#00e5ff'];
const MINIMO_EN_TABLERO = 4;  // el servidor no acepta rondas más chicas

// Celdas (en orden) donde la palabra aparece leída en cualquier dirección
function buscarEnTablero(tablero, palabra) {
    const n = tablero.length;
    const encontradas = [];
    for (let f = 0; f < n; f++) {
        for (let c = 0; c < n; c++) {
            for (const [df, dc] of TODAS_LAS_DIRECCIONES) {
                const celdas = [];
                for (let i = 0; i < palabra.length; i++) {
                    const ff = f + df * i;
                    const cc = c + dc * i;
                    if (ff < 0 || cc < 0 || ff >= n || cc >= n || tablero[ff][cc] !== palabra[i]) break;
                    celdas.push([ff, cc]);
                }
                if (celdas.length === palabra.length) encontradas.push(celdas);
            }
        }
    }
    return encontradas;
}

// Una palabra está bien escondida si aparece en un solo lugar (un palíndromo
// como LEVEL se lee en ambos sentidos sobre las mismas celdas: cuenta como uno)
function apareceUnaVez(tablero, palabra) {
    const lugares = new Set(buscarEnTablero(tablero, palabra)
        .map((celdas) => celdas.map(([f, c]) => `${f},${c}`).sort().join('|')));
    return lugares.size === 1;
}

// Arma la cuadrícula. Devuelve null si no logra esconder al menos MINIMO_EN_TABLERO.
function generarSopa(palabras, n, direcciones) {
    // RUN no puede ir en la misma ronda que RUNNER (ni que RENNUR al revés): siempre
    // se leería dentro de la otra. La más corta se queda fuera y vuelve a la bolsa.
    const ordenadas = [];
    palabras.slice().sort((a, b) => b.letras.length - a.letras.length).forEach((p) => {
        const alReves = p.letras.split('').reverse().join('');
        if (!ordenadas.some((o) => o.letras.includes(p.letras) || o.letras.includes(alReves))) ordenadas.push(p);
    });
    for (let intento = 0; intento < 40; intento++) {
        const tablero = Array.from({ length: n }, () => Array(n).fill(null));
        const colocadas = [];
        for (const palabra of ordenadas) {
            const letras = palabra.letras;
            for (let prueba = 0; prueba < 150; prueba++) {
                const [df, dc] = direcciones[azar(direcciones.length)];
                const f0 = azar(n);
                const c0 = azar(n);
                const fFin = f0 + df * (letras.length - 1);
                const cFin = c0 + dc * (letras.length - 1);
                if (fFin < 0 || cFin < 0 || fFin >= n || cFin >= n) continue;
                const celdas = [];
                let cabe = true;
                let nuevas = 0;
                for (let i = 0; i < letras.length && cabe; i++) {
                    const actual = tablero[f0 + df * i][c0 + dc * i];
                    if (actual !== null && actual !== letras[i]) cabe = false;
                    if (actual === null) nuevas++;
                    celdas.push([f0 + df * i, c0 + dc * i]);
                }
                // Debe ocupar al menos una celda propia: RUN no puede ir escondida dentro de RUNNING
                if (!cabe || nuevas === 0) continue;
                celdas.forEach(([f, c], i) => { tablero[f][c] = letras[i]; });
                colocadas.push({ palabra, celdas });
                break;
            }
        }
        if (colocadas.length < Math.min(MINIMO_EN_TABLERO, palabras.length)) continue;

        // Relleno al azar; si por casualidad forma otra vez alguna palabra, se rellena de nuevo
        for (let relleno = 0; relleno < 15; relleno++) {
            const lleno = tablero.map((fila) => fila.map((letra) => letra || ABECEDARIO[azar(26)]));
            if (colocadas.every(({ palabra }) => apareceUnaVez(lleno, palabra.letras))) {
                return { tablero: lleno, colocadas };
            }
        }
    }
    return null;
}

function iniciarSopa(juego) {
    const palabras = JSON.parse($('sopaPalabras').textContent);
    const porRonda = Number(juego.dataset.porRonda);
    const tableroEl = $('sopaTablero');
    const listaEl = $('sopaLista');
    const zona = $('sopaZona');
    const final = $('sopaFinal');
    const pronunciar = crearSonido($('sopaSonido'));
    const bolsa = crearBolsa('juegosSopaPendientes', palabras);
    const reloj = crearReloj($('sopaTiempo'));
    const clavesSopa = (p) => ['letras:' + p.letras, 'es:' + normalizar(p.es)];

    let nivel = DIRECCIONES[leerPreferencia('juegosSopaNivel')] ? leerPreferencia('juegosSopaNivel') : 'facil';
    let ronda = [];          // [{palabra, celdas, encontrada, color}]
    let celdasEl = [];       // botones de la cuadrícula por [fila][columna]
    let inicioSel = null;    // [fila, columna] de la primera letra tocada
    let errores = 0;
    let pistas = 0;
    let bloqueado = false;

    // ── Dificultad ──
    const botonesNivel = [...juego.querySelectorAll('.sopa-nivel')];
    function pintarNivel() {
        botonesNivel.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.nivel === nivel)));
    }
    botonesNivel.forEach((boton) => boton.addEventListener('click', () => {
        if (boton.dataset.nivel === nivel) return;
        nivel = boton.dataset.nivel;
        guardarPreferencia('juegosSopaNivel', nivel);
        pintarNivel();
        // La ronda a medias no se jugó: sus palabras vuelven a la bolsa
        bolsa.devolver(ronda.map((r) => r.palabra.id));
        nuevaRonda();
    }));

    // En el celular la cuadrícula es más chica para que las letras se puedan tocar
    const tamano = () => (window.innerWidth < 576 ? 8 : 10);

    function nuevaRonda() {
        const n = tamano();
        let sopa = null;
        for (let intento = 0; intento < 5 && !sopa; intento++) {
            const elegidas = bolsa.sacar(Math.min(porRonda, palabras.length), clavesSopa, (p) => p.letras.length <= n);
            sopa = generarSopa(elegidas, n, DIRECCIONES[nivel]);
            if (!sopa) bolsa.devolver(elegidas.map((p) => p.id));
            else {
                const fuera = elegidas.filter((p) => !sopa.colocadas.some((c) => c.palabra === p));
                bolsa.devolver(fuera.map((p) => p.id));
            }
        }
        if (!sopa) {
            zona.innerHTML = '<p class="juegos-vacio">No se pudo armar la sopa con tus palabras. Agrega algunas más cortas e inténtalo de nuevo.</p>';
            return;
        }

        ronda = mezclar(sopa.colocadas).map((c, i) => ({ ...c, encontrada: false, color: COLORES_SOPA[i % COLORES_SOPA.length] }));
        errores = 0;
        pistas = 0;
        inicioSel = null;
        bloqueado = false;
        dibujarTablero(sopa.tablero);
        dibujarLista();
        actualizarBarra();
        final.hidden = true;
        zona.hidden = false;
        reloj.empezar();
    }

    function dibujarTablero(tablero) {
        const n = tablero.length;
        tableroEl.style.setProperty('--n', n);
        celdasEl = tablero.map((fila, f) => fila.map((letra, c) => {
            const celda = document.createElement('button');
            celda.type = 'button';
            celda.className = 'sopa-celda';
            celda.textContent = letra;
            celda.dataset.f = f;
            celda.dataset.c = c;
            celda.setAttribute('aria-label', `${letra}, fila ${f + 1}, columna ${c + 1}`);
            return celda;
        }));
        tableroEl.replaceChildren(...celdasEl.flat());
    }

    function dibujarLista() {
        listaEl.replaceChildren(...ronda.map((r, i) => {
            const item = document.createElement('li');
            item.dataset.i = i;
            item.style.setProperty('--color', r.color);
            const significado = document.createElement('span');
            significado.className = 'sopa-significado';
            significado.textContent = r.palabra.es;
            const ingles = document.createElement('span');
            ingles.className = 'sopa-ingles';
            ingles.lang = 'en';
            ingles.textContent = r.palabra.en;
            const largo = document.createElement('span');
            largo.className = 'sopa-largo';
            largo.textContent = `${r.palabra.letras.length} letras`;
            item.append(significado, largo, ingles);
            return item;
        }));
    }

    function actualizarBarra() {
        $('sopaEncontradas').textContent = ronda.filter((r) => r.encontrada).length;
        $('sopaTotal').textContent = ronda.length;
        $('sopaErrores').textContent = errores;
        $('sopaPistas').textContent = pistas;
    }

    // Celdas en línea recta entre dos puntos (fila, columna o diagonal); null si no hay línea
    function linea([f1, c1], [f2, c2]) {
        const df = Math.sign(f2 - f1);
        const dc = Math.sign(c2 - c1);
        const largo = Math.max(Math.abs(f2 - f1), Math.abs(c2 - c1));
        if (!(f1 === f2 || c1 === c2 || Math.abs(f2 - f1) === Math.abs(c2 - c1))) return null;
        return Array.from({ length: largo + 1 }, (_, i) => [f1 + df * i, c1 + dc * i]);
    }

    const celdaDe = ([f, c]) => celdasEl[f][c];
    const posicion = (el) => [Number(el.dataset.f), Number(el.dataset.c)];

    function limpiarMarcas(clase) {
        tableroEl.querySelectorAll(`.${clase}`).forEach((el) => el.classList.remove(clase));
    }

    // Vista previa: al pasar el mouse se ilumina la línea desde la primera letra
    tableroEl.addEventListener('pointerover', (e) => {
        const celda = e.target.closest('.sopa-celda');
        if (!celda || !inicioSel || bloqueado) return;
        limpiarMarcas('previa');
        (linea(inicioSel, posicion(celda)) || []).forEach((p) => celdaDe(p).classList.add('previa'));
    });
    tableroEl.addEventListener('pointerleave', () => limpiarMarcas('previa'));

    tableroEl.addEventListener('click', (e) => {
        const celda = e.target.closest('.sopa-celda');
        if (!celda || bloqueado) return;
        const pos = posicion(celda);

        if (!inicioSel) {
            inicioSel = pos;
            celda.classList.add('inicio');
            return;
        }
        if (inicioSel[0] === pos[0] && inicioSel[1] === pos[1]) {   // tocar la misma letra la suelta
            celda.classList.remove('inicio');
            limpiarMarcas('previa');
            inicioSel = null;
            return;
        }
        const celdas = linea(inicioSel, pos);
        if (!celdas) {                // no forma línea recta: esta pasa a ser la primera letra
            limpiarMarcas('inicio');
            inicioSel = pos;
            celda.classList.add('inicio');
            return;
        }

        limpiarMarcas('inicio');
        limpiarMarcas('previa');
        inicioSel = null;
        const leida = celdas.map((p) => celdaDe(p).textContent).join('');
        const alReves = leida.split('').reverse().join('');
        const acierto = ronda.find((r) => !r.encontrada && (r.palabra.letras === leida || r.palabra.letras === alReves));

        if (acierto) {
            marcarEncontrada(acierto);
        } else {
            errores++;
            actualizarBarra();
            bloqueado = true;
            celdas.forEach((p) => celdaDe(p).classList.add('fallida'));
            setTimeout(() => {
                limpiarMarcas('fallida');
                bloqueado = false;
            }, 600);
        }
    });

    function marcarEncontrada(r) {
        r.encontrada = true;
        r.celdas.forEach((p) => {
            const el = celdaDe(p);
            el.classList.add('encontrada');
            el.classList.remove('pista');
            el.style.setProperty('--color', r.color);
        });
        listaEl.querySelector(`[data-i="${ronda.indexOf(r)}"]`).classList.add('hecha');
        pronunciar(r.palabra.en);
        actualizarBarra();
        if (ronda.every((x) => x.encontrada)) setTimeout(terminar, 500);
    }

    // Pista: ilumina la primera letra de una palabra que falte
    $('sopaPista').addEventListener('click', () => {
        const faltan = ronda.filter((r) => !r.encontrada && !celdaDe(r.celdas[0]).classList.contains('pista'));
        if (!faltan.length || zona.hidden) return;
        const r = faltan[azar(faltan.length)];
        celdaDe(r.celdas[0]).classList.add('pista');
        listaEl.querySelector(`[data-i="${ronda.indexOf(r)}"]`).classList.add('con-pista');
        pistas++;
        actualizarBarra();
    });

    function terminar() {
        const tiempo = reloj.parar();
        const perfecta = errores === 0 && pistas === 0;
        $('sopaFinalIcono').textContent = perfecta ? '🏆' : errores <= 2 ? '🎉' : '💪';
        $('sopaFinalTitulo').textContent = perfecta ? '¡Sopa perfecta!' : errores <= 2 ? '¡Muy bien!' : '¡Sopa completa, sigue practicando!';
        $('sopaFinalTiempo').textContent = formatoTiempo(tiempo);
        $('sopaFinalErrores').textContent = errores;
        $('sopaFinalPistas').textContent = pistas;

        zona.hidden = true;
        final.hidden = false;
        $('sopaOtra').focus();
        guardarResultado(juego.dataset.resultadoUrl,
            { ids: ronda.map((r) => r.palabra.id), errores, segundos: tiempo, pistas, nivel }, $('sopaFinalNota'));
    }

    $('sopaOtra').addEventListener('click', nuevaRonda);
    pintarNivel();
    nuevaRonda();
}

// ═══════════════════════════ Ahorcado ═══════════════════════════

const VIDAS_AHORCADO = 6;  // una por cada parte del dibujo

// Cómo va una palabra según las letras ya usadas (`usadas` es un Set en mayúsculas)
function estadoAhorcado(letras, usadas) {
    const errores = [...usadas].filter((l) => !letras.includes(l)).length;
    return {
        casillas: [...letras].map((l) => (usadas.has(l) ? l : '')),
        errores,
        ganada: [...letras].every((l) => usadas.has(l)),
        perdida: errores >= VIDAS_AHORCADO,
    };
}

function iniciarAhorcado(juego) {
    const palabras = JSON.parse($('ahorcadoPalabras').textContent);
    const porRonda = Number(juego.dataset.porRonda);
    const zona = $('ahorcadoZona');
    const teclado = $('ahorcadoTeclado');
    const veredicto = $('ahorcadoVeredicto');
    const final = $('ahorcadoFinal');
    const botonPista = $('ahorcadoPista');
    const partes = [...$('ahorcadoDibujo').querySelectorAll('.ahorcado-parte')];
    const pronunciar = crearSonido($('ahorcadoSonido'));
    const bolsa = crearBolsa('juegosAhorcadoPendientes', palabras);
    const reloj = crearReloj($('ahorcadoTiempo'));

    let ronda = [];
    let indice = 0;            // palabra de la ronda que se está jugando
    let usadas = new Set();
    let terminada = false;     // la palabra actual ya se ganó o se perdió
    let pistaUsada = false;
    let aciertos = 0;
    let errores = 0;
    let pistas = 0;

    const teclas = new Map([...ABECEDARIO].map((letra) => {
        const tecla = document.createElement('button');
        tecla.type = 'button';
        tecla.className = 'ahorcado-tecla';
        tecla.textContent = letra;
        tecla.dataset.letra = letra;
        return [letra, tecla];
    }));
    teclado.replaceChildren(...teclas.values());

    function nuevaRonda() {
        ronda = bolsa.sacar(Math.min(porRonda, palabras.length), (p) => ['letras:' + p.letras]);
        indice = 0;
        aciertos = 0;
        errores = 0;
        pistas = 0;
        $('ahorcadoTotal').textContent = ronda.length;
        $('ahorcadoPistas').textContent = 0;
        final.hidden = true;
        zona.hidden = false;
        reloj.empezar();
        mostrarPalabra();
    }

    function mostrarPalabra() {
        const palabra = ronda[indice];
        usadas = new Set();
        terminada = false;
        pistaUsada = false;
        $('ahorcadoNumero').textContent = indice + 1;
        $('ahorcadoEjemplo').textContent = palabra.pistas[azar(palabra.pistas.length)];
        teclas.forEach((tecla) => { tecla.disabled = false; tecla.className = 'ahorcado-tecla'; });
        veredicto.hidden = true;
        teclado.hidden = false;
        botonPista.disabled = false;
        dibujar();
    }

    function dibujar() {
        const estado = estadoAhorcado(ronda[indice].letras, usadas);
        $('ahorcadoCasillas').replaceChildren(...estado.casillas.map((letra) => {
            const casilla = document.createElement('span');
            casilla.className = 'ahorcado-casilla';
            casilla.textContent = letra;
            return casilla;
        }));
        $('ahorcadoVidas').textContent = VIDAS_AHORCADO - estado.errores;
        partes.forEach((parte, i) => parte.classList.toggle('visible', i < estado.errores));
        return estado;
    }

    function probar(letra) {
        if (terminada || usadas.has(letra)) return;
        const acierto = ronda[indice].letras.includes(letra);
        usadas.add(letra);
        const tecla = teclas.get(letra);
        tecla.disabled = true;
        tecla.classList.add(acierto ? 'acertada' : 'fallida');
        if (!acierto) errores++;
        const estado = dibujar();
        if (estado.ganada || estado.perdida) cerrarPalabra(estado.ganada);
    }

    function cerrarPalabra(ganada) {
        const palabra = ronda[indice];
        terminada = true;
        if (ganada) aciertos++;
        botonPista.disabled = true;
        $('ahorcadoVeredictoTitulo').textContent = ganada ? '¡Correcto!' : 'Se acabaron las vidas';
        $('ahorcadoRespuesta').textContent = palabra.en;
        $('ahorcadoSignificado').textContent = palabra.es;
        $('ahorcadoSiguiente').textContent = indice + 1 < ronda.length ? 'Siguiente palabra' : 'Ver resultado';
        teclado.hidden = true;
        veredicto.hidden = false;
        $('ahorcadoSiguiente').focus();
        pronunciar(palabra.en);
    }

    function terminar() {
        const tiempo = reloj.parar();
        const perfecta = errores === 0 && pistas === 0;
        const todas = aciertos === ronda.length;
        $('ahorcadoFinalIcono').textContent = perfecta ? '🏆' : todas ? '🎉' : '💪';
        $('ahorcadoFinalTitulo').textContent = perfecta ? '¡Ronda perfecta!' : todas ? '¡Las adivinaste todas!' : '¡Ronda completa, sigue practicando!';
        $('ahorcadoFinalAciertos').textContent = `${aciertos}/${ronda.length}`;
        $('ahorcadoFinalErrores').textContent = errores;
        $('ahorcadoFinalPistas').textContent = pistas;
        $('ahorcadoFinalTiempo').textContent = formatoTiempo(tiempo);

        zona.hidden = true;
        final.hidden = false;
        $('ahorcadoOtra').focus();
        guardarResultado(juego.dataset.resultadoUrl,
            { ids: ronda.map((p) => p.id), errores, segundos: tiempo, pistas }, $('ahorcadoFinalNota'));
    }

    teclado.addEventListener('click', (e) => {
        const tecla = e.target.closest('.ahorcado-tecla');
        if (tecla) probar(tecla.dataset.letra);
    });

    document.addEventListener('keydown', (e) => {
        // La tarjeta de la frase del día puede estar abierta encima del juego
        if (zona.hidden || e.ctrlKey || e.metaKey || e.altKey || document.querySelector('.frase-dia-fondo:not([hidden])')) return;
        const letra = e.key.toUpperCase();
        if (e.key.length === 1 && teclas.has(letra)) probar(letra);
    });

    // Pista: revela una letra que falte, una vez por palabra
    botonPista.addEventListener('click', () => {
        if (terminada || pistaUsada) return;
        const faltan = [...new Set(ronda[indice].letras)].filter((l) => !usadas.has(l));
        pistaUsada = true;
        pistas++;
        botonPista.disabled = true;
        $('ahorcadoPistas').textContent = pistas;
        probar(faltan[azar(faltan.length)]);
    });

    $('ahorcadoSiguiente').addEventListener('click', () => {
        indice++;
        if (indice < ronda.length) mostrarPalabra();
        else terminar();
    });
    $('ahorcadoOtra').addEventListener('click', nuevaRonda);
    nuevaRonda();
}

// ═══════════════════════════ Caza de patos ═══════════════════════════

const VIDAS_PATOS = 3;
const PATOS_EN_PANTALLA = 4;
const SVG_NS = 'http://www.w3.org/2000/svg';
const VUELO_PATOS = 78;       // % de alto del cielo por donde vuelan; abajo está la escopeta
const ANGULO_ESCOPETA = 70;   // lo máximo que gira hacia cada lado
const PLUMAS = 14;

// El pato correcto y otros con palabra y significado distintos, en orden al azar:
// si dos patos compartieran significado, ambos serían respuestas válidas
function opcionesPatos(objetivo, palabras, cantidad) {
    const ingles = new Set([normalizar(objetivo.en)]);
    const espanol = new Set([normalizar(objetivo.es)]);
    const otros = [];
    for (const p of mezclar(palabras)) {
        if (otros.length === cantidad - 1) break;
        if (ingles.has(normalizar(p.en)) || espanol.has(normalizar(p.es))) continue;
        ingles.add(normalizar(p.en));
        espanol.add(normalizar(p.es));
        otros.push(p);
    }
    return mezclar([objetivo, ...otros]);
}

// Segundos que tarda el pato en cruzar: cada objetivo de la ronda va más rápido
const duracionPato = (indice) => Math.max(4.5, 9 - indice * 0.9);

// Grados que gira la escopeta para apuntar de `origen` a `punto` (0 = recto hacia arriba)
function anguloEscopeta(origen, punto) {
    const grados = Math.atan2(punto.x - origen.x, origen.y - punto.y) * (180 / Math.PI);
    return Math.max(-ANGULO_ESCOPETA, Math.min(ANGULO_ESCOPETA, grados));
}

function iniciarPatos(juego) {
    const palabras = JSON.parse($('patosPalabras').textContent);
    const porRonda = Number(juego.dataset.porRonda);
    const zona = $('patosZona');
    const cielo = $('patosCielo');
    const final = $('patosFinal');
    const mensaje = $('patosMensaje');
    const efectos = $('patosEfectos');
    const escopeta = $('patosEscopeta');
    const pronunciar = crearSonido($('patosSonido'));
    const bolsa = crearBolsa('juegosPatosPendientes', palabras);
    const reloj = crearReloj($('patosTiempo'));
    const clavesPatos = (p) => ['en:' + normalizar(p.en), 'es:' + normalizar(p.es)];

    let ronda = [];
    let indice = 0;
    let objetivo = null;
    let resuelto = false;      // este objetivo ya se cazó, se escapó o se acabó la ronda
    let vidas = VIDAS_PATOS;
    let aciertos = 0;
    let errores = 0;
    let escape = null;         // temporizador del pato correcto

    function crearPato(palabra, fila, filas, segundos) {
        const pato = document.createElement('button');
        const deIzquierda = azar(2) === 0;
        const salida = `${deIzquierda ? -150 : cielo.clientWidth + 10}px`;
        const llegada = `${deIzquierda ? cielo.clientWidth + 10 : -150}px`;
        pato.type = 'button';
        pato.className = deIzquierda ? 'pato' : 'pato al-reves';
        pato.dataset.id = palabra.id;
        pato.style.top = `${(fila * VUELO_PATOS) / filas}%`;
        pato.style.height = `${VUELO_PATOS / filas}%`;
        pato.style.setProperty('--salida', salida);
        pato.style.setProperty('--llegada', llegada);
        pato.style.setProperty('--segundos', `${segundos}s`);

        const cuerpo = document.createElement('span');
        cuerpo.className = 'pato-cuerpo';
        const dibujo = document.createElementNS(SVG_NS, 'svg');
        dibujo.setAttribute('class', 'pato-dibujo');
        const uso = document.createElementNS(SVG_NS, 'use');
        uso.setAttribute('href', '#patoDibujo');
        dibujo.append(uso);
        const texto = document.createElement('span');
        texto.className = 'pato-palabra';
        texto.lang = 'en';
        texto.textContent = palabra.en;
        cuerpo.append(dibujo, texto);
        pato.append(cuerpo);
        return pato;
    }

    function nuevaRonda() {
        ronda = bolsa.sacar(Math.min(porRonda, palabras.length), clavesPatos);
        indice = 0;
        vidas = VIDAS_PATOS;
        aciertos = 0;
        errores = 0;
        $('patosTotal').textContent = ronda.length;
        $('patosVidas').textContent = vidas;
        final.hidden = true;
        zona.hidden = false;
        reloj.empezar();
        mostrarObjetivo();
    }

    function mostrarObjetivo() {
        objetivo = ronda[indice];
        resuelto = false;
        mensaje.textContent = '';
        $('patosNumero').textContent = indice + 1;
        $('patosSignificado').textContent = objetivo.es;

        const opciones = opcionesPatos(objetivo, palabras, PATOS_EN_PANTALLA);
        const segundos = duracionPato(indice);
        cielo.replaceChildren(...opciones.map((p, fila) => crearPato(
            p, fila, opciones.length, p === objetivo ? segundos : segundos * (0.9 + Math.random() * 0.3))));
        escape = setTimeout(seEscapo, segundos * 1000);
    }

    function perderVida() {
        errores++;
        vidas--;
        $('patosVidas').textContent = vidas;
    }

    function apuntar(e) {
        const caja = escopeta.getBoundingClientRect();
        const origen = { x: caja.left + caja.width / 2, y: caja.bottom };
        escopeta.style.setProperty('--angulo', `${anguloEscopeta(origen, { x: e.clientX, y: e.clientY })}deg`);
    }

    function disparar() {
        escopeta.classList.remove('disparando');
        void escopeta.offsetWidth;   // reinicia la animación aunque se dispare seguido
        escopeta.classList.add('disparando');
    }

    // Destello de impacto y explosión de plumas donde estaba el pato
    function estallar(pato) {
        const dibujo = pato.querySelector('.pato-dibujo').getBoundingClientRect();
        const base = efectos.getBoundingClientRect();
        const impacto = document.createElement('div');
        impacto.className = 'pato-impacto';
        impacto.style.left = `${dibujo.left + dibujo.width / 2 - base.left}px`;
        impacto.style.top = `${dibujo.top + dibujo.height / 2 - base.top}px`;

        const destello = document.createElement('span');
        destello.className = 'pato-destello';
        const plumas = Array.from({ length: PLUMAS }, (_, i) => {
            const pluma = document.createElement('span');
            const direccion = (i / PLUMAS) * 2 * Math.PI + Math.random() * 0.4;
            const distancia = 45 + Math.random() * 65;
            pluma.className = i % 3 === 0 ? 'pato-pluma clara' : 'pato-pluma';
            pluma.style.setProperty('--x', `${Math.cos(direccion) * distancia}px`);
            pluma.style.setProperty('--y', `${Math.sin(direccion) * distancia}px`);
            pluma.style.setProperty('--giro', `${azar(360)}deg`);
            return pluma;
        });
        impacto.append(destello, ...plumas);
        efectos.append(impacto);
        setTimeout(() => impacto.remove(), 950);
    }

    // Después de resolver un objetivo: deja ver el resultado y sigue
    function continuar(pausa) {
        setTimeout(() => {
            if (vidas === 0) return terminar();
            indice++;
            if (indice < ronda.length) mostrarObjetivo();
            else terminar();
        }, pausa);
    }

    function seEscapo() {
        resuelto = true;
        perderVida();
        mensaje.textContent = `Se escapó: era "${objetivo.en}"`;
        continuar(1300);
    }

    cielo.addEventListener('pointermove', apuntar);

    cielo.addEventListener('click', (e) => {
        // Disparar al aire no cuesta vidas: solo cuenta darle a un pato
        apuntar(e);
        disparar();
        const pato = e.target.closest('.pato');
        if (!pato || resuelto || pato.disabled) return;

        if (pato.dataset.id === String(objetivo.id)) {
            resuelto = true;
            clearTimeout(escape);
            aciertos++;
            pato.classList.add('cazado');
            estallar(pato);
            mensaje.textContent = '¡Le diste!';
            pronunciar(objetivo.en);
            continuar(850);
            return;
        }

        pato.disabled = true;
        pato.classList.add('fallado');
        perderVida();
        if (vidas === 0) {
            resuelto = true;
            clearTimeout(escape);
            mensaje.textContent = `Sin vidas: era "${objetivo.en}"`;
            continuar(1300);
        } else {
            mensaje.textContent = 'Ese no era';
        }
    });

    function terminar() {
        const tiempo = reloj.parar();
        // Los patos que quedaron sin jugar cuentan como errores en la precisión
        const sinJugar = vidas === 0 ? ronda.length - indice - 1 : 0;
        const perfecta = errores === 0;
        $('patosFinalIcono').textContent = perfecta ? '🏆' : vidas > 0 ? '🎉' : '💪';
        $('patosFinalTitulo').textContent = perfecta ? '¡Ronda perfecta!' : vidas > 0 ? '¡Muy bien!' : 'Se acabaron las vidas';
        $('patosFinalAciertos').textContent = `${aciertos}/${ronda.length}`;
        $('patosFinalErrores').textContent = errores;
        $('patosFinalTiempo').textContent = formatoTiempo(tiempo);

        cielo.replaceChildren();
        zona.hidden = true;
        final.hidden = false;
        $('patosOtra').focus();
        guardarResultado(juego.dataset.resultadoUrl,
            { ids: ronda.map((p) => p.id), errores: errores + sinJugar, segundos: tiempo }, $('patosFinalNota'));
    }

    $('patosOtra').addEventListener('click', nuevaRonda);
    nuevaRonda();
}

// ═══════════════════════════ Crucigrama ═══════════════════════════

const LADO_CRUCIGRAMA = 13;      // filas y columnas máximas: más no cabe en el celular
const MINIMO_EN_CRUCIGRAMA = 4;  // el servidor no acepta rondas más chicas
const INTENTOS_CRUCIGRAMA = 40;
const DIRECCIONES_CRUCIGRAMA = { h: [0, 1], v: [1, 0] };

const claveCelda = (f, c) => `${f},${c}`;

// Cuántas letras comparte la palabra con el tablero en esa posición, o -1 si no cabe:
// fuera de las palabras que cruza no puede tocar ninguna letra, porque formaría otra palabra
function crucesAlColocar(celdas, letras, f0, c0, dir) {
    const [df, dc] = DIRECCIONES_CRUCIGRAMA[dir];
    if (celdas.has(claveCelda(f0 - df, c0 - dc))) return -1;
    if (celdas.has(claveCelda(f0 + df * letras.length, c0 + dc * letras.length))) return -1;
    let cruces = 0;
    for (let i = 0; i < letras.length; i++) {
        const f = f0 + df * i;
        const c = c0 + dc * i;
        const celda = celdas.get(claveCelda(f, c));
        if (celda) {
            if (celda.letra !== letras[i] || celda.dirs.includes(dir)) return -1;
            cruces++;
        } else if (celdas.has(claveCelda(f + dc, c + df)) || celdas.has(claveCelda(f - dc, c - df))) {
            return -1;
        }
    }
    return cruces;
}

function intentarCrucigrama(palabras, maximo) {
    const celdas = new Map();
    const colocadas = [];
    let caja = null;
    let cruces = 0;

    const cajaCon = (largo, f, c, dir) => {
        const [df, dc] = DIRECCIONES_CRUCIGRAMA[dir];
        const fFin = f + df * (largo - 1);
        const cFin = c + dc * (largo - 1);
        return caja
            ? { f0: Math.min(caja.f0, f), c0: Math.min(caja.c0, c), f1: Math.max(caja.f1, fFin), c1: Math.max(caja.c1, cFin) }
            : { f0: f, c0: c, f1: fFin, c1: cFin };
    };
    const cabe = (k) => k.f1 - k.f0 < LADO_CRUCIGRAMA && k.c1 - k.c0 < LADO_CRUCIGRAMA;

    function colocar(palabra, f, c, dir) {
        const [df, dc] = DIRECCIONES_CRUCIGRAMA[dir];
        caja = cajaCon(palabra.letras.length, f, c, dir);
        [...palabra.letras].forEach((letra, i) => {
            const clave = claveCelda(f + df * i, c + dc * i);
            const celda = celdas.get(clave);
            if (celda) celda.dirs.push(dir);
            else celdas.set(clave, { letra, dirs: [dir] });
        });
        colocadas.push({ palabra, fila: f, columna: c, dir });
    }

    // Busca dónde cruza mejor: muchos cruces y un tablero compacto
    function mejorLugar(palabra) {
        let mejor = null;
        for (const [clave, celda] of celdas) {
            if (celda.dirs.length > 1) continue;
            const [f, c] = clave.split(',').map(Number);
            const dir = celda.dirs[0] === 'h' ? 'v' : 'h';
            const [df, dc] = DIRECCIONES_CRUCIGRAMA[dir];
            [...palabra.letras].forEach((letra, i) => {
                if (letra !== celda.letra) return;
                const f0 = f - df * i;
                const c0 = c - dc * i;
                const cruza = crucesAlColocar(celdas, palabra.letras, f0, c0, dir);
                if (cruza < 1) return;
                const k = cajaCon(palabra.letras.length, f0, c0, dir);
                if (!cabe(k)) return;
                const puntos = cruza * 10 - (k.f1 - k.f0 + k.c1 - k.c0) + Math.random() * 3;
                if (!mejor || puntos > mejor.puntos) mejor = { f0, c0, dir, cruza, puntos };
            });
        }
        return mejor;
    }

    const orden = mezclar(palabras).sort((a, b) => b.letras.length - a.letras.length);
    colocar(orden[0], 0, 0, azar(2) ? 'h' : 'v');
    for (const palabra of orden.slice(1)) {
        if (colocadas.length === maximo) break;
        const lugar = mejorLugar(palabra);
        if (lugar) {
            colocar(palabra, lugar.f0, lugar.c0, lugar.dir);
            cruces += lugar.cruza;
        }
    }
    return { colocadas, caja, cruces };
}

// Numera las palabras de arriba abajo y de izquierda a derecha, y deja el tablero
// empezando en la fila 0 y la columna 0. Dos palabras pueden compartir número.
function terminarCrucigrama({ colocadas, caja }) {
    const items = colocadas.map((c) => ({ ...c, fila: c.fila - caja.f0, columna: c.columna - caja.c0 }));
    const inicios = [...new Set(items.map((i) => claveCelda(i.fila, i.columna)))]
        .map((k) => k.split(',').map(Number))
        .sort((a, b) => a[0] - b[0] || a[1] - b[1])
        .map(([f, c]) => claveCelda(f, c));
    items.forEach((i) => { i.numero = inicios.indexOf(claveCelda(i.fila, i.columna)) + 1; });
    return { filas: caja.f1 - caja.f0 + 1, columnas: caja.c1 - caja.c0 + 1, colocadas: items };
}

// Prueba varios órdenes y se queda con el de más palabras, más cruces y menos tamaño.
// Devuelve null si no logra cruzar al menos MINIMO_EN_CRUCIGRAMA.
function generarCrucigrama(palabras, maximo) {
    if (!palabras.length) return null;
    let mejor = null;
    const lado = (t) => t.caja.f1 - t.caja.f0 + t.caja.c1 - t.caja.c0;
    for (let intento = 0; intento < INTENTOS_CRUCIGRAMA; intento++) {
        const prueba = intentarCrucigrama(palabras, maximo);
        if (!mejor
            || prueba.colocadas.length > mejor.colocadas.length
            || (prueba.colocadas.length === mejor.colocadas.length
                && (prueba.cruces > mejor.cruces || (prueba.cruces === mejor.cruces && lado(prueba) < lado(mejor))))) {
            mejor = prueba;
        }
    }
    return mejor.colocadas.length >= MINIMO_EN_CRUCIGRAMA ? terminarCrucigrama(mejor) : null;
}

function iniciarCrucigrama(juego) {
    const palabras = JSON.parse($('cruciPalabras').textContent);
    const porRonda = Number(juego.dataset.porRonda);
    const zona = $('cruciZona');
    const rejilla = $('cruciRejilla');
    const final = $('cruciFinal');
    const mensaje = $('cruciMensaje');
    const pronunciar = crearSonido($('cruciSonido'));
    const bolsa = crearBolsa('juegosCrucigramaPendientes', palabras);
    const reloj = crearReloj($('cruciTiempo'));
    const clavesCruci = (p) => ['letras:' + p.letras, 'es:' + normalizar(p.es)];

    let ronda = [];            // [{palabra, numero, dir, celdas: [claves], resuelta}]
    let casillas = new Map();  // clave -> {input, letra, fila, columna}
    let activa = null;         // palabra en la que se está escribiendo
    let ultimaClave = null;    // casilla tocada, para cambiar de dirección al tocarla otra vez
    let terminado = false;
    let errores = 0;
    let pistas = 0;

    function nuevaRonda() {
        let tablero = null;
        for (let intento = 0; intento < 5 && !tablero; intento++) {
            // Se sacan más de las que caben: no todas logran cruzarse
            const candidatas = bolsa.sacar(Math.min(porRonda + 4, palabras.length), clavesCruci);
            tablero = generarCrucigrama(candidatas, porRonda);
            const usadas = tablero ? tablero.colocadas.map((c) => c.palabra.id) : [];
            bolsa.devolver(candidatas.map((p) => p.id).filter((id) => !usadas.includes(id)));
        }
        if (!tablero) {
            zona.innerHTML = '<p class="juegos-vacio">No se pudo armar el crucigrama con tus palabras. Agrega algunas más e inténtalo de nuevo.</p>';
            return;
        }

        ronda = tablero.colocadas.map((c) => {
            const [df, dc] = DIRECCIONES_CRUCIGRAMA[c.dir];
            return {
                palabra: c.palabra,
                numero: c.numero,
                dir: c.dir,
                celdas: [...c.palabra.letras].map((_, i) => claveCelda(c.fila + df * i, c.columna + dc * i)),
                resuelta: false,
            };
        });
        errores = 0;
        pistas = 0;
        activa = null;
        ultimaClave = null;
        terminado = false;
        dibujarRejilla(tablero);
        dibujarPistas();
        $('cruciTotal').textContent = ronda.length;
        $('cruciPistas').textContent = 0;
        actualizarBarra();
        mensaje.textContent = '';
        $('cruciBotones').hidden = false;
        $('cruciPista').disabled = false;
        final.hidden = true;
        zona.hidden = false;
        reloj.empezar();
        activar(ronda[0], ronda[0].celdas[0]);
    }

    function dibujarRejilla(tablero) {
        const letras = new Map();
        tablero.colocadas.forEach((c) => {
            const [df, dc] = DIRECCIONES_CRUCIGRAMA[c.dir];
            [...c.palabra.letras].forEach((l, i) => letras.set(claveCelda(c.fila + df * i, c.columna + dc * i), l));
        });
        const numeros = new Map(tablero.colocadas.map((c) => [claveCelda(c.fila, c.columna), c.numero]));

        casillas = new Map();
        rejilla.style.setProperty('--columnas', tablero.columnas);
        const hijos = [];
        for (let f = 0; f < tablero.filas; f++) {
            for (let c = 0; c < tablero.columnas; c++) {
                const clave = claveCelda(f, c);
                const celda = document.createElement('div');
                if (!letras.has(clave)) {
                    celda.className = 'cruci-vacia';
                    hijos.push(celda);
                    continue;
                }
                celda.className = 'cruci-celda';
                if (numeros.has(clave)) {
                    const numero = document.createElement('span');
                    numero.className = 'cruci-numero';
                    numero.textContent = numeros.get(clave);
                    celda.append(numero);
                }
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'cruci-letra';
                input.autocomplete = 'off';
                input.autocapitalize = 'characters';
                input.spellcheck = false;
                input.dataset.clave = clave;
                input.setAttribute('aria-label', `Fila ${f + 1}, columna ${c + 1}`);
                celda.append(input);
                casillas.set(clave, { input, letra: letras.get(clave), fila: f, columna: c });
                hijos.push(celda);
            }
        }
        rejilla.replaceChildren(...hijos);
    }

    function dibujarPistas() {
        const lista = (dir) => ronda.filter((r) => r.dir === dir).sort((a, b) => a.numero - b.numero).map((r) => {
            const item = document.createElement('li');
            item.dataset.i = ronda.indexOf(r);
            const numero = document.createElement('strong');
            numero.textContent = `${r.numero}.`;
            const texto = document.createElement('span');
            texto.textContent = ` ${r.palabra.es} (${r.palabra.letras.length})`;
            item.append(numero, texto);
            return item;
        });
        $('cruciHorizontales').replaceChildren(...lista('h'));
        $('cruciVerticales').replaceChildren(...lista('v'));
    }

    function actualizarBarra() {
        $('cruciResueltas').textContent = ronda.filter((r) => r.resuelta).length;
        $('cruciErrores').textContent = errores;
    }

    const palabrasDe = (clave) => ronda.filter((r) => r.celdas.includes(clave));

    function activar(palabra, clave) {
        activa = palabra;
        ultimaClave = clave;
        casillas.forEach((c, k) => c.input.classList.toggle('en-palabra', palabra.celdas.includes(k)));
        document.querySelectorAll('.cruci-lista li').forEach((li) => {
            li.classList.toggle('activa', ronda[li.dataset.i] === palabra);
        });
        const flecha = palabra.dir === 'h' ? '→' : '↓';
        $('cruciActiva').textContent = `${palabra.numero} ${flecha} ${palabra.palabra.es} (${palabra.palabra.letras.length})`;
        casillas.get(clave).input.focus();
        casillas.get(clave).input.select();   // escribir encima reemplaza la letra
    }

    const bloqueada = (clave) => casillas.get(clave).input.readOnly;

    // Avanza dentro de la palabra saltando las casillas ya resueltas
    function mover(clave, paso) {
        const celdas = activa.celdas;
        for (let i = celdas.indexOf(clave) + paso; i >= 0 && i < celdas.length; i += paso) {
            if (!bloqueada(celdas[i])) {
                activar(activa, celdas[i]);
                return true;
            }
        }
        return false;
    }

    function escribir(clave, letra) {
        const casilla = casillas.get(clave);
        casilla.escrita = letra;
        casilla.input.value = letra;
        casilla.input.classList.remove('incorrecta');
    }

    rejilla.addEventListener('click', (e) => {
        const input = e.target.closest('.cruci-letra');
        if (!input || terminado) return;
        const clave = input.dataset.clave;
        const opciones = palabrasDe(clave);
        // Tocar otra vez una casilla donde se cruzan dos palabras cambia de dirección
        let palabra = opciones.includes(activa) ? activa : opciones[0];
        if (clave === ultimaClave && opciones.length > 1) palabra = opciones.find((o) => o !== activa);
        activar(palabra, clave);
    });

    rejilla.addEventListener('input', (e) => {
        const input = e.target;
        const clave = input.dataset.clave;
        // En el celular no siempre llega la tecla: se lee lo que quedó escrito
        const letras = input.value.toUpperCase().replace(/[^A-Z]/g, '');
        // Si la casilla no quedó seleccionada, ignora la letra que ya estaba
        const anterior = casillas.get(clave).escrita;
        const nuevas = letras.length === 2 && letras[0] === anterior ? letras.slice(1) : letras;
        if (!nuevas) escribir(clave, '');
        // Varias letras a la vez (pegar, autocompletar) se reparten por las casillas
        let actual = clave;
        for (const letra of nuevas) {
            escribir(actual, letra);
            if (!mover(actual, 1)) break;
            actual = ultimaClave;
        }
    });

    rejilla.addEventListener('keydown', (e) => {
        const input = e.target.closest('.cruci-letra');
        if (!input || terminado) return;
        const clave = input.dataset.clave;
        const { fila, columna } = casillas.get(clave);
        const flechas = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };

        if (e.key === 'Backspace') {
            if (bloqueada(clave)) {
                e.preventDefault();
                mover(clave, -1);
            } else if (!input.value) {
                e.preventDefault();
                if (mover(clave, -1)) escribir(ultimaClave, '');
            }
        } else if (flechas[e.key]) {
            e.preventDefault();
            const [df, dc] = flechas[e.key];
            const destino = claveCelda(fila + df, columna + dc);
            if (!casillas.has(destino)) return;
            const opciones = palabrasDe(destino);
            const dir = df ? 'v' : 'h';
            activar(opciones.find((o) => o.dir === dir) || opciones[0], destino);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            comprobar();
        } else if (e.key.length === 1 && /[a-z]/i.test(e.key) && bloqueada(clave)) {
            mover(clave, 1);
        }
    });

    document.querySelectorAll('.cruci-lista').forEach((lista) => lista.addEventListener('click', (e) => {
        const item = e.target.closest('li');
        if (!item || terminado) return;
        const palabra = ronda[item.dataset.i];
        activar(palabra, palabra.celdas.find((c) => !bloqueada(c)) || palabra.celdas[0]);
    }));

    function resolver(r) {
        r.resuelta = true;
        r.celdas.forEach((clave) => {
            const { input } = casillas.get(clave);
            input.readOnly = true;
            input.classList.remove('incorrecta');
            input.classList.add('correcta');
        });
        const item = document.querySelector(`.cruci-lista li[data-i="${ronda.indexOf(r)}"]`);
        item.classList.add('hecha');
        item.querySelector('span').textContent += ` — ${r.palabra.en}`;
    }

    const textoDe = (r) => r.celdas.map((clave) => casillas.get(clave).input.value).join('');

    // Solo se revisan las palabras completas: cada una mal escrita cuenta como un error
    function comprobar() {
        if (terminado) return;
        const llenas = ronda.filter((r) => !r.resuelta && textoDe(r).length === r.celdas.length);
        if (!llenas.length) {
            mensaje.textContent = 'Completa una palabra para comprobarla.';
            return;
        }
        const buenas = llenas.filter((r) => textoDe(r) === r.palabra.letras);
        const malas = llenas.filter((r) => !buenas.includes(r));
        errores += malas.length;
        malas.forEach((r) => r.celdas.forEach((clave) => {
            const { input, letra } = casillas.get(clave);
            input.classList.toggle('incorrecta', input.value !== letra);
        }));
        buenas.forEach(resolver);
        if (buenas.length) pronunciar(buenas[buenas.length - 1].palabra.en);
        actualizarBarra();
        mensaje.textContent = malas.length ? 'Hay letras por corregir.' : '¡Bien!';
        if (ronda.every((r) => r.resuelta)) setTimeout(() => terminar(false), 500);
    }

    // Pista: pone una letra correcta en la palabra elegida
    $('cruciPista').addEventListener('click', () => {
        if (terminado || !activa) return;
        const faltan = activa.celdas.filter((c) => !bloqueada(c) && casillas.get(c).input.value !== casillas.get(c).letra);
        if (!faltan.length) {
            mensaje.textContent = 'A esa palabra no le falta ninguna letra: compruébala.';
            return;
        }
        const clave = faltan[azar(faltan.length)];
        const { input, letra } = casillas.get(clave);
        escribir(clave, letra);
        input.readOnly = true;
        input.classList.add('revelada');
        pistas++;
        $('cruciPistas').textContent = pistas;
        if (pistas === ronda.length) $('cruciPista').disabled = true;   // el servidor no acepta más
    });

    // Ver solución: las palabras que faltaban cuentan como errores
    $('cruciSolucion').addEventListener('click', () => {
        if (terminado) return;
        const faltan = ronda.filter((r) => !r.resuelta);
        errores += faltan.length;
        faltan.forEach((r) => {
            r.celdas.forEach((clave) => { casillas.get(clave).input.value = casillas.get(clave).letra; });
            resolver(r);
        });
        terminar(true);
    });

    function terminar(conSolucion) {
        terminado = true;
        const tiempo = reloj.parar();
        const perfecta = errores === 0 && pistas === 0;
        $('cruciFinalIcono').textContent = perfecta ? '🏆' : conSolucion ? '💪' : '🎉';
        $('cruciFinalTitulo').textContent = perfecta ? '¡Crucigrama perfecto!' : conSolucion ? 'Repasa estas palabras' : '¡Crucigrama completo!';
        $('cruciFinalAciertos').textContent = ronda.length;
        $('cruciFinalErrores').textContent = errores;
        $('cruciFinalPistas').textContent = pistas;
        $('cruciFinalTiempo').textContent = formatoTiempo(tiempo);

        actualizarBarra();
        mensaje.textContent = '';
        $('cruciBotones').hidden = true;
        $('cruciPista').disabled = true;
        // El tablero queda a la vista para repasar las respuestas
        final.hidden = false;
        $('cruciOtra').focus();
        guardarResultado(juego.dataset.resultadoUrl,
            { ids: ronda.map((r) => r.palabra.id), errores, segundos: tiempo, pistas }, $('cruciFinalNota'));
    }

    $('cruciComprobar').addEventListener('click', comprobar);
    $('cruciOtra').addEventListener('click', nuevaRonda);
    nuevaRonda();
}

// ═══════════════════════════ Carrera del mono ═══════════════════════════

const VIDAS_MONO = 3;
const LIANAS = 3;
const RACHA_BANANA = 3;         // aciertos seguidos para ganar una banana
const OBSTACULOS = ['roca', 'tronco', 'charco'];
const POSICION_MONO = 14;       // % de la escena donde corre el mono
const TIEMPO_SALTO = 350;       // ms desde el acierto hasta pasar por encima del obstáculo

// Hay que leer la frase: empieza con calma y nunca baja de lo que toma leerla
const segundosMono = (indice) => Math.max(5, 10 - indice * 0.5);

const ganaBanana = (racha) => racha > 0 && racha % RACHA_BANANA === 0;

function iniciarMono(juego) {
    const palabras = JSON.parse($('monoPalabras').textContent);
    const porRonda = Number(juego.dataset.porRonda);
    const zona = $('monoZona');
    const escena = $('monoEscena');
    const personaje = $('monoPersonaje');
    const obstaculo = $('monoObstaculo');
    const lianas = $('monoLianas');
    const aprende = $('monoAprende');
    const final = $('monoFinal');
    const frase = $('monoFrase');
    const pronunciar = crearSonido($('monoSonido'));
    const bolsa = crearBolsa('juegosMonoPendientes', palabras);
    const reloj = crearReloj($('monoTiempo'));
    const clavesMono = (p) => ['letras:' + p.letras];

    let ronda = [];
    let indice = 0;
    let objetivo = null;
    let ejemplo = 0;           // cuál de los ejemplos de la palabra se está usando
    let resuelto = false;
    let vidas = VIDAS_MONO;
    let aciertos = 0;
    let errores = 0;
    let racha = 0;
    let bananas = 0;
    let repaso = [];           // palabras falladas, para repasarlas al final
    let llegada = null;        // temporizador del obstáculo
    let vuelo = null;          // animación del obstáculo

    function nuevaRonda() {
        ronda = bolsa.sacar(Math.min(porRonda, palabras.length), clavesMono);
        indice = 0;
        vidas = VIDAS_MONO;
        aciertos = 0;
        errores = 0;
        racha = 0;
        bananas = 0;
        repaso = [];
        $('monoTotal').textContent = ronda.length;
        $('monoVidas').textContent = vidas;
        $('monoBananas').textContent = 0;
        final.hidden = true;
        zona.hidden = false;
        reloj.empezar();
        mostrarObstaculo();
    }

    function mostrarObstaculo() {
        objetivo = ronda[indice];
        resuelto = false;
        ejemplo = azar(objetivo.pistas.length);
        $('monoNumero').textContent = indice + 1;
        frase.textContent = objetivo.pistas[ejemplo];
        frase.classList.remove('completa');
        personaje.classList.remove('saltando', 'tropezando');
        escena.classList.remove('parada');
        aprende.hidden = true;
        lianas.hidden = false;

        lianas.replaceChildren(...opcionesPatos(objetivo, palabras, LIANAS).map((p, i) => {
            const liana = document.createElement('button');
            liana.type = 'button';
            liana.className = 'mono-liana';
            liana.dataset.id = p.id;
            liana.lang = 'en';
            const numero = document.createElement('span');
            numero.textContent = i + 1;
            // En minúsculas: una mayúscula guardada en el vocabulario delataría la respuesta
            liana.append(numero, ` ${p.en.toLowerCase()}`);
            return liana;
        }));

        const segundos = segundosMono(indice);
        // El obstáculo cruza toda la escena; llega al mono cuando se cumple el tiempo
        const fraccion = (100 - POSICION_MONO) / 115;
        obstaculo.className = `mono-obstaculo ${OBSTACULOS[azar(OBSTACULOS.length)]}`;
        vuelo = obstaculo.animate([{ left: '100%' }, { left: '-15%' }],
            { duration: (segundos * 1000) / fraccion, fill: 'forwards' });
        llegada = setTimeout(() => tropezar('Se acabó el tiempo'), segundos * 1000);
    }

    function completarFrase() {
        const texto = objetivo.frases[ejemplo];
        frase.textContent = texto;
        frase.classList.add('completa');
        return texto;
    }

    function saltar() {
        resuelto = true;
        clearTimeout(llegada);
        aciertos++;
        racha++;
        const faltan = ((segundosMono(indice) * 1000) - (vuelo.currentTime || 0)) / TIEMPO_SALTO;
        vuelo.playbackRate = Math.max(1, faltan);
        personaje.classList.add('saltando');
        if (ganaBanana(racha)) {
            bananas++;
            $('monoBananas').textContent = bananas;
            const premio = $('monoPremio');
            premio.classList.remove('visible');
            void premio.offsetWidth;
            premio.classList.add('visible');
        }
        pronunciar(completarFrase());
        setTimeout(siguiente, 1700);
    }

    // Tropezar detiene la carrera y enseña la respuesta: sigue cuando lo decidas
    function tropezar(titulo) {
        resuelto = true;
        clearTimeout(llegada);
        vuelo.pause();
        errores++;
        vidas--;
        racha = 0;
        $('monoVidas').textContent = vidas;
        personaje.classList.add('tropezando');
        escena.classList.add('parada');
        const texto = completarFrase();
        repaso.push({ palabra: objetivo, frase: texto });

        $('monoAprendeTitulo').textContent = titulo;
        $('monoAprendePalabra').textContent = objetivo.en;
        $('monoAprendeSignificado').textContent = objetivo.es;
        $('monoAprendeFrase').textContent = texto;
        $('monoSeguir').textContent = vidas === 0 || indice + 1 === ronda.length ? 'Ver resultado' : 'Seguir corriendo';
        lianas.hidden = true;
        aprende.hidden = false;
        $('monoSeguir').focus();
        pronunciar(texto);
    }

    function siguiente() {
        vuelo.cancel();
        if (vidas === 0) return terminar();
        indice++;
        if (indice < ronda.length) mostrarObstaculo();
        else terminar();
    }

    function elegir(liana) {
        if (resuelto) return;
        if (liana.dataset.id === String(objetivo.id)) {
            liana.classList.add('acertada');
            saltar();
        } else {
            liana.classList.add('fallida');
            tropezar('Esa no era');
        }
    }

    function dibujarRepaso() {
        $('monoRepaso').hidden = repaso.length === 0;
        $('monoRepasoLista').replaceChildren(...repaso.map(({ palabra, frase: texto }) => {
            const item = document.createElement('li');
            const ingles = document.createElement('strong');
            ingles.lang = 'en';
            ingles.textContent = palabra.en;
            const significado = document.createElement('span');
            significado.textContent = ` — ${palabra.es}`;
            const ejemploEl = document.createElement('em');
            ejemploEl.lang = 'en';
            ejemploEl.textContent = texto;
            item.append(ingles, significado, ejemploEl);
            return item;
        }));
    }

    function terminar() {
        const tiempo = reloj.parar();
        // Los obstáculos que quedaron sin jugar cuentan como errores en la precisión
        const sinJugar = vidas === 0 ? ronda.length - indice - 1 : 0;
        const perfecta = errores === 0;
        $('monoFinalIcono').textContent = perfecta ? '🏆' : vidas > 0 ? '🎉' : '💪';
        $('monoFinalTitulo').textContent = perfecta ? '¡Carrera perfecta!' : vidas > 0 ? '¡Llegaste a la meta!' : 'Se acabaron las vidas';
        $('monoFinalAciertos').textContent = `${aciertos}/${ronda.length}`;
        $('monoFinalBananas').textContent = bananas;
        $('monoFinalErrores').textContent = errores;
        $('monoFinalTiempo').textContent = formatoTiempo(tiempo);
        dibujarRepaso();

        zona.hidden = true;
        final.hidden = false;
        $('monoOtra').focus();
        guardarResultado(juego.dataset.resultadoUrl,
            { ids: ronda.map((p) => p.id), errores: errores + sinJugar, segundos: tiempo }, $('monoFinalNota'));
    }

    lianas.addEventListener('click', (e) => {
        const liana = e.target.closest('.mono-liana');
        if (liana) elegir(liana);
    });

    document.addEventListener('keydown', (e) => {
        // La tarjeta de la frase del día puede estar abierta encima del juego
        if (zona.hidden || resuelto || e.ctrlKey || e.metaKey || e.altKey
            || document.querySelector('.frase-dia-fondo:not([hidden])')) return;
        const liana = lianas.children[Number(e.key) - 1];
        if (liana) elegir(liana);
    });

    $('monoSeguir').addEventListener('click', siguiente);
    $('monoOtra').addEventListener('click', nuevaRonda);
    nuevaRonda();
}

if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        const unir = $('juegoUnir');
        if (unir) iniciarUnir(unir);
        const sopa = $('juegoSopa');
        if (sopa) iniciarSopa(sopa);
        const ahorcado = $('juegoAhorcado');
        if (ahorcado) iniciarAhorcado(ahorcado);
        const patos = $('juegoPatos');
        if (patos) iniciarPatos(patos);
        const crucigrama = $('juegoCrucigrama');
        if (crucigrama) iniciarCrucigrama(crucigrama);
        const mono = $('juegoMono');
        if (mono) iniciarMono(mono);
    });
}

// Los tests (app/test/test_juegos.py) cargan la lógica de los juegos con Node
if (typeof module !== 'undefined') {
    module.exports = {
        generarSopa, buscarEnTablero, DIRECCIONES, estadoAhorcado, VIDAS_AHORCADO,
        opcionesPatos, duracionPato, anguloEscopeta, VIDAS_PATOS, PATOS_EN_PANTALLA,
        generarCrucigrama, DIRECCIONES_CRUCIGRAMA, LADO_CRUCIGRAMA,
        segundosMono, ganaBanana, VIDAS_MONO, LIANAS,
    };
}
