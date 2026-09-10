function toggleForms(target) {
    const loginSec = document.getElementById('loginSection');
    const registerSec = document.getElementById('registerSection');

    if (target === 'register') {
        // Ocultar Login (Mover a la izquierda)
        loginSec.style.transform = 'translateX(-100%)';
        loginSec.style.opacity = '0';
        loginSec.style.visibility = 'hidden';
        loginSec.style.pointerEvents = 'none';

        // Mostrar Registro (Traer de la derecha)
        registerSec.style.transform = 'translateX(0)';
        registerSec.style.opacity = '1';
        registerSec.style.visibility = 'visible';
        registerSec.style.pointerEvents = 'auto';
    } else {
        // Mostrar Login (Traer del centro)
        loginSec.style.transform = 'translateX(0)';
        loginSec.style.opacity = '1';
        loginSec.style.visibility = 'visible';
        loginSec.style.pointerEvents = 'auto';

        // Ocultar Registro (Mover a la derecha)
        registerSec.style.transform = 'translateX(100%)';
        registerSec.style.opacity = '0';
        registerSec.style.visibility = 'hidden';
        registerSec.style.pointerEvents = 'none';
    }
}

function checkPasswordMatch() {
    const pwd = document.getElementById('regPasswordUser').value;
    const confirm = document.getElementById('regPasswordConfirm').value;
    const errorDiv = document.getElementById('passwordError');
    const btnRegister = document.getElementById('btnRegister');

    if (confirm === "") {
        errorDiv.style.display = 'none';
        btnRegister.disabled = false;
        return true;
    }

    if (pwd !== confirm) {
        errorDiv.style.display = 'block';
        btnRegister.disabled = true;
        return false;
    } else {
        errorDiv.style.display = 'none';
        btnRegister.disabled = false;
        return true;
    }
}

function validatePasswords(e) {
    if (!checkPasswordMatch()) {
        e.preventDefault();
        return false;
    }
    return true;
}

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector('i');

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
}
