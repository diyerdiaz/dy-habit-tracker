// Efecto del mouse: un resplandor suave (del color del tema; azul en Inglés) que sigue al puntero con un
// pequeño retraso y se intensifica sobre botones y enlaces. Solo en equipos
// con mouse y si el sistema no pide reducir las animaciones.
(function () {
    const conMouse = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!conMouse || sinMovimiento) return;

    const INTERACTIVOS = 'a, button, label, input, select, textarea, [role="button"]';

    function iniciar() {
        const luz = document.createElement('div');
        luz.className = 'cursor-luz';
        luz.setAttribute('aria-hidden', 'true');
        document.body.appendChild(luz);

        const mouse = { x: 0, y: 0 };
        const pos = { x: 0, y: 0 };
        let animando = false;

        function cuadro() {
            pos.x += (mouse.x - pos.x) * 0.15;
            pos.y += (mouse.y - pos.y) * 0.15;
            luz.style.transform = `translate(${pos.x}px, ${pos.y}px) translate(-50%, -50%)`;
            if (Math.abs(mouse.x - pos.x) > 0.3 || Math.abs(mouse.y - pos.y) > 0.3) {
                requestAnimationFrame(cuadro);
            } else {
                animando = false;  // quieto: no gasta batería
            }
        }

        document.addEventListener('mousemove', (e) => {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
            if (!luz.classList.contains('visible')) {
                pos.x = mouse.x;
                pos.y = mouse.y;
                luz.classList.add('visible');
            }
            if (!animando) {
                animando = true;
                requestAnimationFrame(cuadro);
            }
        }, { passive: true });

        document.addEventListener('mouseover', (e) => {
            luz.classList.toggle('sobre-boton', !!e.target.closest(INTERACTIVOS));
        });
        document.documentElement.addEventListener('mouseleave', () => luz.classList.remove('visible'));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
