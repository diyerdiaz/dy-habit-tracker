// Temas aleatorios: ruleta que saca un tema, temporizador para explicarlo y
// calificación al terminar (se guarda en el servidor).
document.addEventListener('DOMContentLoaded', function () {
    var ruleta = document.getElementById('ruleta');
    if (!ruleta) return;

    var btnGirar = document.getElementById('btnGirar');
    var espera = document.getElementById('espera');
    var resultado = document.getElementById('resultado');
    var titulo = document.getElementById('temaTitulo');
    var notas = document.getElementById('temaNotas');
    var reloj = document.getElementById('reloj');
    var relojTiempo = document.getElementById('relojTiempo');
    var relojAvance = document.getElementById('relojAvance');
    var btnEmpezar = document.getElementById('btnEmpezar');
    var btnPausa = document.getElementById('btnPausa');
    var btnTerminar = document.getElementById('btnTerminar');
    var otro = document.getElementById('minutosOtro');
    var CIRCUNFERENCIA = 2 * Math.PI * 52;

    var temaActual = null;
    var total = 0, restante = 0, intervalo = null, corriendo = false;

    function minutosElegidos() {
        var propio = parseInt(otro.value, 10);
        if (propio >= 1 && propio <= parseInt(otro.max, 10)) return propio;
        var marcado = document.querySelector('input[name="minutos"]:checked');
        return marcado ? parseInt(marcado.value, 10) : 2;
    }

    function formato(seg) {
        var m = Math.floor(seg / 60), s = seg % 60;
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    function pintarReloj() {
        relojTiempo.textContent = formato(restante);
        relojAvance.style.strokeDashoffset = total ? CIRCUNFERENCIA * (1 - restante / total) : 0;
        reloj.classList.toggle('urgente', corriendo && restante <= 10);
    }

    function prepararReloj() {
        detener();
        total = restante = minutosElegidos() * 60;
        pintarReloj();
        btnEmpezar.hidden = false;
        btnEmpezar.innerHTML = '<i class="bi bi-mic-fill"></i> Empezar a explicar';
        btnPausa.hidden = true;
        btnTerminar.hidden = true;
    }

    function detener() {
        clearInterval(intervalo);
        intervalo = null;
        corriendo = false;
    }

    function sonar() {
        try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            [0, 0.25, 0.5].forEach(function (t) {
                var osc = ctx.createOscillator(), vol = ctx.createGain();
                osc.frequency.value = 880;
                vol.gain.setValueAtTime(0.2, ctx.currentTime + t);
                vol.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.2);
                osc.connect(vol); vol.connect(ctx.destination);
                osc.start(ctx.currentTime + t); osc.stop(ctx.currentTime + t + 0.2);
            });
        } catch (e) { /* sin sonido, no pasa nada */ }
    }

    function arrancar() {
        if (corriendo || restante <= 0) return;
        corriendo = true;
        btnEmpezar.hidden = true;
        btnPausa.hidden = false;
        btnPausa.innerHTML = '<i class="bi bi-pause-fill"></i> Pausa';
        btnTerminar.hidden = false;
        intervalo = setInterval(function () {
            restante -= 1;
            pintarReloj();
            if (restante <= 0) {
                detener();
                sonar();
                terminar();
            }
        }, 1000);
    }

    // ── Calificar y guardar ──
    var modalEl = document.getElementById('calificarModal');
    var modal = new bootstrap.Modal(modalEl);
    var estrellas = document.querySelectorAll('#estrellas button');
    var calificacion = null;

    function marcarEstrellas(n) {
        estrellas.forEach(function (b, i) {
            b.querySelector('i').className = 'bi ' + (i < n ? 'bi-star-fill' : 'bi-star');
        });
    }

    estrellas.forEach(function (b) {
        b.addEventListener('click', function () {
            calificacion = parseInt(b.dataset.valor, 10);
            marcarEstrellas(calificacion);
        });
    });

    function terminar() {
        detener();
        var hablados = total - restante;
        if (!temaActual || hablados <= 0) { prepararReloj(); return; }
        calificacion = null;
        marcarEstrellas(0);
        document.getElementById('calificarTiempo').textContent =
            'Hablaste ' + formato(hablados) + ' de ' + formato(total) + ' sobre «' + temaActual.titulo + '».';
        modalEl.dataset.hablados = hablados;
        modal.show();
    }

    document.getElementById('btnGuardarSesion').addEventListener('click', function () {
        fetch(ruleta.dataset.sesion, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'fetch' },
            body: JSON.stringify({
                tema: temaActual.id, objetivo: total,
                hablados: parseInt(modalEl.dataset.hablados, 10), calificacion: calificacion,
            }),
        }).then(function () { window.location.reload(); });
    });

    // ── Girar la ruleta ──
    function girar() {
        btnGirar.disabled = true;
        btnGirar.classList.add('girando');
        detener();
        fetch(ruleta.dataset.girar, { method: 'POST', headers: { 'X-Requested-With': 'fetch' } })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success) throw new Error(data.error);
                espera.hidden = true;
                resultado.hidden = false;
                notas.hidden = true;
                btnEmpezar.hidden = btnPausa.hidden = btnTerminar.hidden = true;
                var opciones = data.opciones.length ? data.opciones : [data.tema.titulo];
                var vueltas = 0, maximo = 18;
                titulo.classList.add('girando');
                (function paso() {
                    titulo.textContent = opciones[Math.floor(Math.random() * opciones.length)];
                    vueltas += 1;
                    if (vueltas < maximo) {
                        setTimeout(paso, 40 + vueltas * 9);  // cada vez más lento, como una ruleta
                        return;
                    }
                    temaActual = data.tema;
                    titulo.textContent = data.tema.titulo;
                    titulo.classList.remove('girando');
                    titulo.classList.remove('cayo');
                    void titulo.offsetWidth;
                    titulo.classList.add('cayo');
                    if (data.tema.notas) {
                        notas.textContent = 'Pistas: ' + data.tema.notas;
                        notas.hidden = false;
                    }
                    prepararReloj();
                    btnGirar.disabled = false;
                    btnGirar.classList.remove('girando');
                    btnGirar.querySelector('span').textContent = 'Otro tema';
                })();
            })
            .catch(function (e) {
                btnGirar.disabled = false;
                btnGirar.classList.remove('girando');
                alert(e.message || 'No se pudo sacar un tema.');
            });
    }

    btnGirar.addEventListener('click', girar);
    btnEmpezar.addEventListener('click', arrancar);
    btnTerminar.addEventListener('click', terminar);
    btnPausa.addEventListener('click', function () {
        if (corriendo) {
            detener();
            btnPausa.innerHTML = '<i class="bi bi-play-fill"></i> Seguir';
        } else {
            arrancar();
        }
    });

    // Cambiar el tiempo antes de empezar actualiza el reloj
    document.querySelectorAll('input[name="minutos"]').forEach(function (r) {
        r.addEventListener('change', function () { otro.value = ''; if (temaActual && !corriendo) prepararReloj(); });
    });
    otro.addEventListener('input', function () { if (temaActual && !corriendo) prepararReloj(); });

    // ── Editar y eliminar temas ──
    var editarModal = new bootstrap.Modal(document.getElementById('editarModal'));
    document.querySelectorAll('[data-editar]').forEach(function (b) {
        b.addEventListener('click', function () {
            document.getElementById('editarForm').action = b.dataset.url;
            document.getElementById('editarTitulo').value = b.dataset.titulo;
            document.getElementById('editarNotas').value = b.dataset.notas;
            editarModal.show();
        });
    });
    document.querySelectorAll('form[data-confirmar]').forEach(function (f) {
        f.addEventListener('submit', function (e) {
            if (!confirm(f.dataset.confirmar)) e.preventDefault();
        });
    });

    // Que no se pierda la explicación si se cierra la página a mitad
    window.addEventListener('beforeunload', function (e) {
        if (corriendo) { e.preventDefault(); e.returnValue = ''; }
    });
});
