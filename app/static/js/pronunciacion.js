// Pronunciación: se lee el texto en voz alta y cada palabra se pinta de verde
// (dicha bien), rojo (dicha mal o saltada) o se queda gris (todavía no llegas).
// Usa el reconocimiento de voz del navegador (Chrome), en inglés.

const NUMEROS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen',
                 'eighteen', 'nineteen', 'twenty'];

// "Hello," -> "hello", "Don’t" -> "don't", "5" -> "five". Vacío si no tiene letras ni números.
function normalizar(palabra) {
    const limpia = palabra.toLowerCase()
        .replace(/[’‘`]/g, "'")
        .replace(/[^a-z0-9']/g, '')
        .replace(/^'+|'+$/g, '');
    return /^\d+$/.test(limpia) && Number(limpia) < NUMEROS.length ? NUMEROS[Number(limpia)] : limpia;
}

// Lo que dijo la persona, como lista de palabras normalizadas
function palabrasDichas(texto) {
    return texto.split(/[\s\-–—]+/).map(normalizar).filter(Boolean);
}

// Compara las palabras del texto con las dichas y devuelve un estado por cada una:
// 'bien', 'mal' o 'pendiente'. Alinea las dos listas (como un diff) para que una palabra
// saltada o una de más no pinte de rojo todo lo que sigue.
function comparar(objetivo, dichas) {
    const n = objetivo.length, m = dichas.length;
    const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
    for (let i = 1; i <= n; i++) dp[i][0] = i;
    for (let j = 1; j <= m; j++) dp[0][j] = j;
    for (let i = 1; i <= n; i++) {
        for (let j = 1; j <= m; j++) {
            const igual = objetivo[i - 1] === dichas[j - 1] ? 0 : 1;
            dp[i][j] = Math.min(dp[i - 1][j - 1] + igual, dp[i - 1][j] + 1, dp[i][j - 1] + 1);
        }
    }

    // Hasta dónde llegó: el final del texto todavía no leído no cuenta como error
    let hasta = 0;
    for (let i = 1; i <= n; i++) {
        if (dp[i][m] <= dp[hasta][m]) hasta = i;
    }
    if (m === 0) hasta = 0;

    const estados = new Array(n).fill('pendiente');
    let i = hasta, j = m;
    while (i > 0 && j > 0) {
        const igual = objetivo[i - 1] === dichas[j - 1];
        if (dp[i][j] === dp[i - 1][j - 1] + (igual ? 0 : 1)) {
            estados[i - 1] = igual ? 'bien' : 'mal';
            i--; j--;
        } else if (dp[i][j] === dp[i - 1][j] + 1) {
            estados[i - 1] = 'mal';  // se la saltó
            i--;
        } else {
            j--;  // dijo una palabra de más
        }
    }
    while (i > 0) estados[--i] = 'mal';
    return estados;
}

if (typeof module !== 'undefined') {
    module.exports = { normalizar, palabrasDichas, comparar };
}

if (typeof document !== 'undefined') {
    const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;
    const CLAVE_TEXTO = 'pronunciacion-texto';

    const aviso = document.getElementById('pronAviso');
    const textarea = document.getElementById('pronTexto');
    const cajaPalabras = document.getElementById('pronPalabras');
    const btnIniciar = document.getElementById('pronIniciar');
    const btnEditar = document.getElementById('pronEditar');
    const btnReiniciar = document.getElementById('pronReiniciar');
    const resultado = document.getElementById('pronResultado');
    const elBien = document.getElementById('pronBien');
    const elMal = document.getElementById('pronMal');
    const elFalta = document.getElementById('pronFalta');
    const elPorcentaje = document.getElementById('pronPorcentaje');
    const elBarra = document.getElementById('pronBarra');
    const elEscuche = document.getElementById('pronEscuche');

    let spans = [];          // una <span> por palabra del texto
    let objetivo = [];       // las mismas palabras, normalizadas
    let textoAnterior = '';  // lo escuchado en tandas anteriores del micrófono
    let textoTanda = '';     // lo ya confirmado en la tanda actual
    let grabando = false;
    let reconocimiento = null;

    function avisar(texto) {
        aviso.textContent = texto;
        aviso.hidden = !texto;
    }

    try { textarea.value = localStorage.getItem(CLAVE_TEXTO) || ''; } catch (e) { /* sin almacenamiento */ }
    textarea.addEventListener('input', () => {
        try { localStorage.setItem(CLAVE_TEXTO, textarea.value); } catch (e) { /* sin almacenamiento */ }
    });

    // Brave trae el reconocimiento de voz pero lo tiene apagado: siempre falla con "network"
    const esBrave = !!navigator.brave;
    const MENSAJE_BRAVE = 'Brave no permite el reconocimiento de voz. Abre esta página en Google Chrome.';

    if (!Reconocimiento) {
        avisar('Tu navegador no permite el reconocimiento de voz. Abre esta página en Google Chrome.');
        btnIniciar.disabled = true;
    } else if (esBrave) {
        avisar(MENSAJE_BRAVE);
        btnIniciar.disabled = true;
    } else if (!window.isSecureContext) {
        avisar('El micrófono solo funciona si la página está en https.');
        btnIniciar.disabled = true;
    }

    // Arma las palabras del texto dentro de la carpeta, respetando espacios y saltos de línea
    function armarPalabras(texto) {
        cajaPalabras.textContent = '';
        spans = [];
        objetivo = [];
        texto.split(/(\s+)/).forEach((trozo) => {
            if (!trozo) return;
            if (/^\s+$/.test(trozo)) {
                cajaPalabras.appendChild(document.createTextNode(trozo.includes('\n') ? '\n' : ' '));
                return;
            }
            // "well-known" son dos palabras al hablar
            trozo.split(/(?<=[\-–—])/).forEach((parte) => {
                const norm = normalizar(parte);
                if (!norm) {
                    cajaPalabras.appendChild(document.createTextNode(parte));
                    return;
                }
                const span = document.createElement('span');
                span.className = 'pron-palabra';
                span.textContent = parte;
                span.addEventListener('click', () => pronunciar(span));
                cajaPalabras.appendChild(span);
                spans.push(span);
                objetivo.push(norm);
            });
        });
    }

    function pintar(escuchado) {
        const estados = comparar(objetivo, palabrasDichas(escuchado));
        let bien = 0, mal = 0;
        estados.forEach((estado, k) => {
            spans[k].classList.toggle('bien', estado === 'bien');
            spans[k].classList.toggle('mal', estado === 'mal');
            if (estado === 'bien') bien++;
            if (estado === 'mal') mal++;
        });
        const total = estados.length || 1;
        elBien.textContent = bien;
        elMal.textContent = mal;
        elFalta.textContent = estados.length - bien - mal;
        elPorcentaje.textContent = `${Math.round((bien / total) * 100)} %`;
        elBarra.style.width = `${(bien / total) * 100}%`;
        elEscuche.textContent = escuchado.trim() || '—';
        return estados;
    }

    function pronunciar(span) {
        if (grabando) {
            avisar('Detén el micrófono para escuchar la palabra.');
            return;
        }
        if (!window.speechSynthesis) return;
        speechSynthesis.cancel();
        const voz = new SpeechSynthesisUtterance(span.textContent.replace(/[^\w'’\-]/g, ''));
        voz.lang = 'en-US';
        voz.rate = 0.85;
        span.classList.add('sonando');
        voz.onend = voz.onerror = () => span.classList.remove('sonando');
        speechSynthesis.speak(voz);
    }

    function mostrarCarpeta(practicando) {
        textarea.hidden = practicando;
        cajaPalabras.hidden = !practicando;
        btnEditar.hidden = !practicando;
        btnReiniciar.hidden = !practicando;
        resultado.hidden = !practicando;
    }

    function ponerBoton() {
        btnIniciar.classList.toggle('grabando', grabando);
        btnIniciar.querySelector('i').className = grabando ? 'bi bi-stop-fill' : 'bi bi-mic-fill';
        btnIniciar.querySelector('span').textContent = grabando ? 'Detener'
            : (textoAnterior || textoTanda ? 'Continuar' : 'Iniciar');
    }

    function crearReconocimiento() {
        const r = new Reconocimiento();
        r.lang = 'en-US';
        r.interimResults = true;
        // En Android el modo continuo repite frases; ahí se escucha por tandas
        r.continuous = !/Android/i.test(navigator.userAgent);

        r.onresult = (evento) => {
            let confirmado = '', provisional = '';
            for (let k = 0; k < evento.results.length; k++) {
                const frase = evento.results[k][0].transcript + ' ';
                if (evento.results[k].isFinal) confirmado += frase; else provisional += frase;
            }
            textoTanda = confirmado;
            const estados = pintar(textoAnterior + confirmado + provisional);
            // Si ya leyó todo el texto, se apaga solo
            if (!provisional && estados.length && !estados.includes('pendiente')) detener();
        };

        r.onerror = (evento) => {
            if (evento.error === 'no-speech' || evento.error === 'aborted') return;
            const mensajes = {
                'not-allowed': 'Necesito permiso para usar el micrófono. Revísalo en el candado de la barra de direcciones.',
                'audio-capture': 'No encontré ningún micrófono.',
                'network': esBrave ? MENSAJE_BRAVE
                    : 'No se pudo conectar con el reconocimiento de voz. Revisa tu internet o usa Google Chrome.',
            };
            avisar(mensajes[evento.error] || 'No se pudo usar el micrófono.');
            detener();
        };

        // El navegador corta solo tras un silencio: si seguimos grabando, se vuelve a encender
        r.onend = () => {
            textoAnterior += textoTanda;
            textoTanda = '';
            if (grabando) {
                try { r.start(); } catch (e) { detener(); }
            }
        };
        return r;
    }

    function iniciar() {
        const texto = textarea.value.trim();
        if (!texto) {
            avisar('Primero pega un texto en inglés dentro de la carpeta.');
            textarea.focus();
            return;
        }
        avisar('');
        if (textarea.hidden === false) {
            armarPalabras(texto);
            textoAnterior = '';
            pintar('');
            mostrarCarpeta(true);
        }
        if (window.speechSynthesis) speechSynthesis.cancel();
        reconocimiento = reconocimiento || crearReconocimiento();
        grabando = true;
        ponerBoton();
        try { reconocimiento.start(); } catch (e) { /* ya estaba encendido */ }
    }

    // descartar = true bota lo que el micrófono no alcanzó a confirmar (al reiniciar o editar)
    function detener(descartar = false) {
        grabando = false;
        if (reconocimiento) {
            if (descartar) reconocimiento.abort(); else reconocimiento.stop();
        }
        ponerBoton();
    }

    btnIniciar.addEventListener('click', () => (grabando ? detener() : iniciar()));

    btnReiniciar.addEventListener('click', () => {
        detener(true);
        textoAnterior = '';
        textoTanda = '';
        pintar('');
        ponerBoton();
    });

    btnEditar.addEventListener('click', () => {
        detener(true);
        textoAnterior = '';
        textoTanda = '';
        mostrarCarpeta(false);
        ponerBoton();
        textarea.focus();
    });
}
