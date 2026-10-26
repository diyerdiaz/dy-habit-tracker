// Vision Board: descarga un póster (PNG tamaño A4 a 300 ppp) con todas las metas,
// listo para imprimir y pegar en la pared. Se dibuja en un <canvas> en el navegador.
document.addEventListener('DOMContentLoaded', function () {
    var boton = document.getElementById('btnDescargarPoster');
    if (!boton) return;

    var ANCHO = 2480, ALTO = 3508;   // A4 vertical a 300 ppp
    var FRASES = [
        'Lo que visualizas hoy, lo construyes mañana.',
        'Un paso a la vez, pero todos los días.',
        'Tus metas no se cumplen solas: tú las cumples.',
    ];

    function colorTema(nombre, defecto) {
        var valor = getComputedStyle(document.documentElement).getPropertyValue(nombre).trim()
            || getComputedStyle(document.body).getPropertyValue(nombre).trim();
        return valor || defecto;
    }

    function cargarImagen(src) {
        return new Promise(function (resolver) {
            var img = new Image();
            img.onload = function () { resolver(img); };
            img.onerror = function () { resolver(null); };
            img.src = src;
        });
    }

    // Recorta la imagen para llenar el recuadro sin deformarla (como object-fit: cover)
    function dibujarCubriendo(ctx, img, x, y, w, h) {
        var escala = Math.max(w / img.naturalWidth, h / img.naturalHeight);
        var sw = w / escala, sh = h / escala;
        var sx = (img.naturalWidth - sw) / 2, sy = (img.naturalHeight - sh) / 2;
        ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
    }

    // Parte el texto en líneas que quepan en `ancho`; máximo `maxLineas` (con "…")
    function lineasDeTexto(ctx, texto, ancho, maxLineas) {
        var palabras = texto.split(/\s+/), lineas = [], actual = '';
        palabras.forEach(function (p) {
            var prueba = actual ? actual + ' ' + p : p;
            if (ctx.measureText(prueba).width <= ancho || !actual) actual = prueba;
            else { lineas.push(actual); actual = p; }
        });
        if (actual) lineas.push(actual);
        if (lineas.length > maxLineas) {
            lineas = lineas.slice(0, maxLineas);
            var ultima = lineas[maxLineas - 1];
            while (ultima.length > 1 && ctx.measureText(ultima + '…').width > ancho) ultima = ultima.slice(0, -1);
            lineas[maxLineas - 1] = ultima + '…';
        }
        return lineas;
    }

    function rectRedondeado(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
    }

    function dibujarFondo(ctx, vivo) {
        var fondo = ctx.createLinearGradient(0, 0, 0, ALTO);
        fondo.addColorStop(0, '#16002a');
        fondo.addColorStop(1, '#05000a');
        ctx.fillStyle = fondo;
        ctx.fillRect(0, 0, ANCHO, ALTO);
        [[ANCHO * 0.5, 380, 1300], [ANCHO * 0.1, ALTO * 0.6, 1100], [ANCHO * 0.9, ALTO * 0.85, 1100]].forEach(function (b) {
            var brillo = ctx.createRadialGradient(b[0], b[1], 0, b[0], b[1], b[2]);
            brillo.addColorStop(0, vivo + '40');
            brillo.addColorStop(1, vivo + '00');
            ctx.fillStyle = brillo;
            ctx.fillRect(0, 0, ANCHO, ALTO);
        });
    }

    function dibujarEncabezado(ctx, vivo) {
        ctx.textAlign = 'center';
        ctx.textBaseline = 'alphabetic';
        ctx.save();
        ctx.shadowColor = vivo;
        ctx.shadowBlur = 60;
        ctx.fillStyle = vivo;
        ctx.font = "250px 'Kaushan Script', cursive";
        ctx.fillText('Vision Board', ANCHO / 2, 400);
        ctx.restore();

        ctx.fillStyle = 'rgba(255,255,255,0.75)';
        ctx.font = "700 95px 'Caveat', cursive";
        // Solo el año: el póster es para la pared, no lleva conteos de metas
        var texto = String(new Date().getFullYear());
        ctx.fillText(texto, ANCHO / 2, 530);
    }

    function dibujarPolaroid(ctx, meta, img, cx, cy, w, h, angulo) {
        var margen = w * 0.06;
        var alturaPie = w * 0.24;
        var fotoW = w - margen * 2, fotoH = h - margen - alturaPie;

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angulo);
        ctx.translate(-w / 2, -h / 2);

        // Marco de papel con sombra
        ctx.save();
        ctx.shadowColor = 'rgba(0,0,0,0.6)';
        ctx.shadowBlur = 50;
        ctx.shadowOffsetY = 20;
        ctx.fillStyle = '#fbf8f3';
        rectRedondeado(ctx, 0, 0, w, h, 14);
        ctx.fill();
        ctx.restore();

        // Foto
        ctx.save();
        ctx.beginPath();
        ctx.rect(margen, margen, fotoW, fotoH);
        ctx.clip();
        if (img) {
            dibujarCubriendo(ctx, img, margen, margen, fotoW, fotoH);
        } else {
            ctx.fillStyle = '#2a1640';
            ctx.fillRect(margen, margen, fotoW, fotoH);
        }
        ctx.restore();

        // Título escrito a mano en el pie de la foto
        var tamano = Math.min(alturaPie * 0.42, w * 0.11);
        ctx.font = "700 " + tamano + "px 'Caveat', cursive";
        ctx.fillStyle = '#2b1838';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        var lineas = lineasDeTexto(ctx, meta.titulo, fotoW, 2);
        var inicio = margen + fotoH + alturaPie / 2 - (lineas.length - 1) * tamano * 0.5;
        lineas.forEach(function (l, i) { ctx.fillText(l, w / 2, inicio + i * tamano); });

        // Cinta adhesiva del color de la categoría
        ctx.save();
        ctx.translate(w / 2, 0);
        ctx.rotate(-angulo * 1.5 + 0.03);
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = meta.color;
        ctx.fillRect(-w * 0.17, -w * 0.035, w * 0.34, w * 0.09);
        ctx.restore();

        // Sello de meta lograda
        if (meta.cumplida) {
            var r = Math.min(fotoW, fotoH) * 0.2;
            ctx.save();
            ctx.translate(margen + fotoW - r * 1.05, margen + r * 1.05);
            ctx.rotate(-0.25);
            ctx.fillStyle = 'rgba(0, 200, 110, 0.9)';
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = r * 0.06;
            ctx.beginPath();
            ctx.arc(0, 0, r * 0.86, 0, Math.PI * 2);
            ctx.stroke();
            ctx.fillStyle = '#ffffff';
            ctx.font = "700 " + (r * 0.42) + "px 'Caveat', cursive";
            ctx.fillText('¡Lograda!', 0, 0);
            ctx.restore();
        }
        ctx.restore();
    }

    function dibujarPie(ctx, vivo) {
        ctx.textAlign = 'center';
        ctx.textBaseline = 'alphabetic';
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        ctx.font = "700 100px 'Caveat', cursive";
        ctx.fillText('“' + FRASES[new Date().getMonth() % FRASES.length] + '”', ANCHO / 2, ALTO - 190);
        ctx.fillStyle = vivo;
        ctx.font = "600 42px 'Poppins', Arial, sans-serif";
        ctx.fillText('D Y   H A B I T   T R A C K E R', ANCHO / 2, ALTO - 95);
    }

    async function generarPoster(metas) {
        var vivo = colorTema('--tema-vivo', '#d966ff');
        if (!/^#[0-9a-f]{6}$/i.test(vivo)) vivo = '#d966ff';
        await Promise.all([
            document.fonts.load("250px 'Kaushan Script'"),
            document.fonts.load("700 100px 'Caveat'"),
        ]).catch(function () {});
        var imagenes = await Promise.all(metas.map(function (m) { return cargarImagen(m.imagen); }));

        var canvas = document.createElement('canvas');
        canvas.width = ANCHO;
        canvas.height = ALTO;
        var ctx = canvas.getContext('2d');
        dibujarFondo(ctx, vivo);
        dibujarEncabezado(ctx, vivo);

        // Cuadrícula: se prueba cada número de columnas y se queda el que deja las
        // fotos más grandes. Si sobra alto, la polaroid se estira (hasta 1.5 veces su ancho).
        var n = metas.length;
        var areaX = 150, areaY = 640, areaW = ANCHO - 300, areaH = ALTO - 640 - 380;
        var columnas = 1, filas = n, w = 0, h = 0, celdaW = 0, celdaH = 0;
        for (var c = 1; c <= Math.min(n, 6); c++) {
            var f = Math.ceil(n / c);
            var cw = areaW / c, ch = areaH / f;
            var pw = Math.min(cw * 0.84, ch * 0.86 / 1.18);
            var ph = Math.min(ch * 0.86, pw * 1.5);
            if (pw * ph > w * h) { columnas = c; filas = f; w = pw; h = ph; celdaW = cw; celdaH = ch; }
        }

        metas.forEach(function (meta, i) {
            var fila = Math.floor(i / columnas);
            var enFila = Math.min(columnas, n - fila * columnas);
            // La última fila incompleta queda centrada
            var desplazamiento = (columnas - enFila) * celdaW / 2;
            var cx = areaX + desplazamiento + (i % columnas + 0.5) * celdaW;
            var cy = areaY + (fila + 0.5) * celdaH;
            var angulo = ((i * 37) % 9 - 4) * Math.PI / 180;   // -4° a 4°, siempre igual
            dibujarPolaroid(ctx, meta, imagenes[i], cx, cy, w, h, angulo);
        });

        dibujarPie(ctx, vivo);
        return new Promise(function (resolver) { canvas.toBlob(resolver, 'image/png'); });
    }

    boton.addEventListener('click', async function () {
        var metas;
        try { metas = JSON.parse(boton.dataset.metas || '[]'); } catch (e) { metas = []; }
        if (!metas.length) return;
        var etiqueta = boton.querySelector('span');
        var textoOriginal = etiqueta.textContent;
        boton.disabled = true;
        etiqueta.textContent = 'Generando…';
        try {
            var blob = await generarPoster(metas);
            var enlace = document.createElement('a');
            enlace.href = URL.createObjectURL(blob);
            enlace.download = 'vision-board-' + new Date().toISOString().slice(0, 10) + '.png';
            document.body.appendChild(enlace);
            enlace.click();
            enlace.remove();
            setTimeout(function () { URL.revokeObjectURL(enlace.href); }, 5000);
        } catch (e) {
            alert('No se pudo generar la imagen. Inténtalo de nuevo.');
        } finally {
            boton.disabled = false;
            etiqueta.textContent = textoOriginal;
        }
    });
});
