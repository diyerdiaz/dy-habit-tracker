// Pantallas de "recuperar contraseña" (templates/auth/recuperar*.html)

// Código en cuadros: un número por cuadro, salta solo al siguiente,
// "borrar" vuelve al anterior y pegar el código completo llena todos
(function () {
    var cajas = Array.prototype.slice.call(document.querySelectorAll('.codigo-caja'));
    var oculto = document.getElementById('codigo');
    if (!cajas.length || !oculto) return;
    var aviso = document.getElementById('avisoIncompleto');

    function actualizar() {
        oculto.value = cajas.map(function (c) { return c.value; }).join('');
        cajas.forEach(function (c) { c.classList.toggle('llena', c.value !== ''); });
        if (aviso && oculto.value.length === cajas.length) aviso.hidden = true;
    }

    // Reparte los dígitos desde la caja `desde` (sirve para pegar o autocompletar)
    function repartir(desde, texto) {
        var digitos = texto.replace(/\D/g, '').split('');
        var i = desde;
        digitos.forEach(function (d) {
            if (i < cajas.length) { cajas[i].value = d; i += 1; }
        });
        actualizar();
        cajas[Math.min(i, cajas.length - 1)].focus();
    }

    cajas.forEach(function (caja, i) {
        caja.addEventListener('input', function () {
            var valor = caja.value;
            caja.value = '';
            if (valor.replace(/\D/g, '')) repartir(i, valor);
            else actualizar();
        });
        caja.addEventListener('keydown', function (e) {
            if (e.key === 'Backspace' && !caja.value && i > 0) {
                cajas[i - 1].value = '';
                cajas[i - 1].focus();
                actualizar();
                e.preventDefault();
            } else if (e.key === 'ArrowLeft' && i > 0) {
                cajas[i - 1].focus();
                e.preventDefault();
            } else if (e.key === 'ArrowRight' && i < cajas.length - 1) {
                cajas[i + 1].focus();
                e.preventDefault();
            }
        });
        caja.addEventListener('paste', function (e) {
            var texto = (e.clipboardData || window.clipboardData).getData('text');
            e.preventDefault();
            repartir(i, texto);
        });
        caja.addEventListener('focus', function () { caja.select(); });
    });

    document.getElementById('formCodigo').addEventListener('submit', function (e) {
        actualizar();
        if (oculto.value.length !== cajas.length) {
            e.preventDefault();
            if (aviso) aviso.hidden = false;
            var vacia = cajas.find(function (c) { return !c.value; });
            if (vacia) vacia.focus();
        }
    });
})();

// Cuenta regresiva de los 5 minutos del código
(function () {
    var reloj = document.getElementById('cuentaRegresiva');
    if (!reloj) return;
    var restantes = parseInt(reloj.dataset.segundos, 10) || 0;
    function pintar() {
        var m = Math.floor(restantes / 60);
        var s = restantes % 60;
        reloj.textContent = m + ':' + (s < 10 ? '0' : '') + s;
        if (restantes <= 0) {
            clearInterval(intervalo);
            document.getElementById('avisoVencido').hidden = false;
            document.getElementById('btnCodigo').disabled = true;
            document.querySelectorAll('.codigo-caja').forEach(function (c) { c.disabled = true; });
        }
        restantes -= 1;
    }
    var intervalo = setInterval(pintar, 1000);
    pintar();
})();

// Contraseña nueva: avisa si la confirmación no coincide
(function () {
    var form = document.getElementById('formNueva');
    if (!form) return;
    var nueva = document.getElementById('nueva_contrasena');
    var confirmar = document.getElementById('confirmar_contrasena');
    var error = document.getElementById('passwordError');
    function revisar() {
        var distintas = confirmar.value && nueva.value !== confirmar.value;
        error.style.display = distintas ? 'block' : 'none';
        return !distintas;
    }
    nueva.addEventListener('input', revisar);
    confirmar.addEventListener('input', revisar);
    form.addEventListener('submit', function (e) { if (!revisar()) e.preventDefault(); });
})();
