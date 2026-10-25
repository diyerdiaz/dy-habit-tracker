// Juegos de vocabulario. Todas las palabras llegan con la página, así que las
// rondas se arman aquí sin pedir nada al servidor; solo se envía el resultado.
//  - Unir parejas: se toca una palabra en inglés y luego su significado (o al revés).
//  - Sopa de letras: los significados son las pistas; se toca la primera y la
//    última letra de la palabra en inglés dentro de la cuadrícula.

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

if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        const unir = $('juegoUnir');
        if (unir) iniciarUnir(unir);
        const sopa = $('juegoSopa');
        if (sopa) iniciarSopa(sopa);
    });
}

// Los tests (app/test/test_juegos.py) cargan el armado de la sopa con Node
if (typeof module !== 'undefined') {
    module.exports = { generarSopa, buscarEnTablero, DIRECCIONES };
}
