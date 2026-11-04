// Marcar las palabras con las que ya se hizo una frase y contar el avance
const palabrasHechas = document.getElementById('palabrasHechas');

document.querySelectorAll('.palabras-card').forEach((card) => {
    card.addEventListener('click', () => {
        card.classList.toggle('hecha');
        palabrasHechas.textContent = document.querySelectorAll('.palabras-card.hecha').length;
    });
});
