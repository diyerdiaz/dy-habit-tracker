// Brillo e inclinación 3D que sigue al mouse sobre las tarjetas
document.querySelectorAll('.ingles-card').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        card.style.setProperty('--mx', `${(x / rect.width) * 100}%`);
        card.style.setProperty('--my', `${(y / rect.height) * 100}%`);

        const rotateY = ((x / rect.width) - 0.5) * 10;
        const rotateX = ((y / rect.height) - 0.5) * -10;
        card.style.transform = `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-6px)`;
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(600px) rotateX(0deg) rotateY(0deg) translateY(0)';
    });
});

// Animación de aparición al hacer scroll
const inglesFadeSections = document.querySelectorAll('.fade-in-section');
const inglesScrollObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            inglesScrollObserver.unobserve(entry.target);
        }
    });
}, {
    threshold: 0.15,
    rootMargin: "0px 0px -50px 0px"
});

inglesFadeSections.forEach((section) => inglesScrollObserver.observe(section));
