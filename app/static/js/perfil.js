// La foto se sube apenas eliges el archivo
document.getElementById('inputFoto').addEventListener('change', function () {
    if (!this.files.length) return;
    if (this.files[0].size > 8 * 1024 * 1024) {
        alert('La foto pesa demasiado. El máximo es 8 MB.');
        this.value = '';
        return;
    }
    document.querySelector('.perfil-avatar').classList.add('subiendo');
    document.getElementById('formFoto').submit();
});

// Mostrar / ocultar contraseñas
document.querySelectorAll('.perfil-ver').forEach(function (btn) {
    btn.addEventListener('click', function () {
        var input = document.getElementById(btn.dataset.ver);
        var mostrar = input.type === 'password';
        input.type = mostrar ? 'text' : 'password';
        btn.innerHTML = mostrar ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
        btn.setAttribute('aria-label', mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña');
    });
});

// Avisa antes de enviar si la confirmación no coincide
(function () {
    var form = document.getElementById('formContrasena');
    var nueva = document.getElementById('nueva_contrasena');
    var confirmar = document.getElementById('confirmar_contrasena');
    var error = document.getElementById('errorContrasena');
    function revisar() {
        var distintas = confirmar.value && nueva.value !== confirmar.value;
        error.hidden = !distintas;
        return !distintas;
    }
    nueva.addEventListener('input', revisar);
    confirmar.addEventListener('input', revisar);
    form.addEventListener('submit', function (e) { if (!revisar()) e.preventDefault(); });
})();
