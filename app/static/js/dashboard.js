// Sidebar Toggle
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');

sidebarToggle.addEventListener('click', () => {
    sidebarToggle.classList.toggle('active');
    sidebar.classList.toggle('active');
    sidebarOverlay.classList.toggle('active');
});

sidebarOverlay.addEventListener('click', () => {
    sidebarToggle.classList.remove('active');
    sidebar.classList.remove('active');
    sidebarOverlay.classList.remove('active');
});

// Notificaciones Toggle & Lógica
const notificationBellBtn = document.getElementById('notificationBellBtn');
const notificationDropdown = document.getElementById('notificationDropdown');
const notificationBadge = document.getElementById('notificationBadge');
const markAllReadBtn = document.getElementById('markAllRead');

notificationBellBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    notificationDropdown.classList.toggle('active');
});

// Cerrar panel al hacer clic fuera
document.addEventListener('click', (e) => {
    if (!notificationDropdown.contains(e.target) && e.target !== notificationBellBtn) {
        notificationDropdown.classList.remove('active');
    }
});

// Marcar todas como leídas
markAllReadBtn.addEventListener('click', () => {
    const unreadItems = document.querySelectorAll('.notification-item.unread');
    unreadItems.forEach(item => {
        item.classList.remove('unread');
    });
    if (notificationBadge) {
        notificationBadge.style.display = 'none';
    }
});

// Marcar individual como leída
window.markAsRead = function (element) {
    element.classList.remove('unread');
    const unreadItems = document.querySelectorAll('.notification-item.unread');
    if (unreadItems.length === 0 && notificationBadge) {
        notificationBadge.style.display = 'none';
    }
}

// Typing Effect Animation
document.addEventListener('DOMContentLoaded', () => {
    const titleText = "Tu Progreso Personal";
    const typingTitle = document.getElementById('typingTitle');
    const cursor = document.getElementById('cursor');
    const descText = document.getElementById('descText');

    let charIndex = 0;
    function type() {
        if (charIndex < titleText.length) {
            typingTitle.textContent += titleText.charAt(charIndex);
            charIndex++;
            setTimeout(type, 80); // 80ms per character
        } else {
            // Hide cursor after a short delay
            setTimeout(() => {
                cursor.style.display = 'none';
            }, 800);
            // Reveal description text
            descText.style.opacity = '1';
            descText.style.transform = 'translateY(0)';
        }
    }
    // Start typing
    setTimeout(type, 300);

    // Marcar hábitos como hechos hoy desde el dashboard
    document.querySelectorAll('.dashboard-habit-item').forEach(item => {
        item.addEventListener('click', () => {
            const id = item.dataset.id;
            fetch(`/habit/${id}/toggle_today`, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (!data.success) return;
                    const badge = item.querySelector('.dashboard-habit-badge');
                    if (data.done) {
                        badge.textContent = 'Completado';
                        badge.style.background = 'rgba(138, 40, 255, 0.4)';
                        badge.style.border = '1px solid rgba(138, 40, 255, 0.8)';
                        badge.style.color = '';
                    } else {
                        badge.textContent = 'Pendiente';
                        badge.style.background = 'rgba(255, 255, 255, 0.05)';
                        badge.style.border = '1px solid rgba(255, 255, 255, 0.2)';
                        badge.style.color = 'rgba(255,255,255,0.6)';
                    }
                })
                .catch(() => alert('No se pudo actualizar el hábito.'));
        });
    });
});

// 1. Animaciones de Entrada en Scroll (Intersection Observer)
const fadeSections = document.querySelectorAll('.fade-in-section');
const scrollObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            // Trigger any animations inside the section
            animateInsideSection(entry.target);
            scrollObserver.unobserve(entry.target);
        }
    });
}, {
    threshold: 0.15,
    rootMargin: "0px 0px -50px 0px"
});

fadeSections.forEach(section => {
    scrollObserver.observe(section);
});

// Función para disparar animaciones específicas dentro de las tarjetas al hacerse visibles
function animateInsideSection(section) {
    // Animar las barras de gráfico
    const bars = section.querySelectorAll('.chart-bar');
    bars.forEach(bar => {
        const finalHeight = bar.getAttribute('data-height');
        setTimeout(() => {
            bar.style.height = finalHeight;
        }, 100);
    });

    // Animar el círculo de progreso SVG
    const progressCircle = section.querySelector('#progressCircle');
    if (progressCircle) {
        const percentage = +progressCircle.getAttribute('data-percentage');
        const radius = progressCircle.r.baseVal.value;
        const circumference = 2 * Math.PI * radius; // 377 aprox
        const offset = circumference - (circumference * percentage / 100);
        setTimeout(() => {
            progressCircle.style.strokeDashoffset = offset;
        }, 200);
    }

    // Animar barras de progreso horizontales
    const progressBars = section.querySelectorAll('.animate-progress-bar');
    progressBars.forEach(bar => {
        const finalWidth = bar.getAttribute('data-width');
        setTimeout(() => {
            bar.style.width = finalWidth;
        }, 300); // Pequeño retraso para que se vea más natural
    });

    // Animar Gráfico de Radar (Solo si la sección tiene el canvas)
    const radarCanvas = section.querySelector('#habitsRadarChart');
    if (radarCanvas && !radarCanvas.dataset.initialized) {
        radarCanvas.dataset.initialized = 'true';
        const ctx = radarCanvas.getContext('2d');
        const dashboardData = window.DASHBOARD_DATA || { radar_labels: [], radar_data: [] };

        const gradientFill = ctx.createLinearGradient(0, 0, 0, 300);
        gradientFill.addColorStop(0, 'rgba(138, 40, 255, 0.35)');
        gradientFill.addColorStop(1, 'rgba(225, 0, 255, 0.05)');

        new Chart(ctx, {
            type: 'radar',
            data: {
                labels: dashboardData.radar_labels,
                datasets: [{
                    label: 'Cumplimiento de Hoy',
                    data: dashboardData.radar_data,
                    backgroundColor: gradientFill,
                    borderColor: '#e100ff',
                    pointBackgroundColor: 'rgba(20, 0, 40, 0.95)',
                    pointBorderColor: '#e100ff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#e100ff',
                    borderWidth: 2.5,
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 3000,
                    easing: 'easeOutQuint'
                },
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255, 255, 255, 0.15)' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)', circular: true },
                        pointLabels: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            font: { size: 12, family: "'Inter', sans-serif", style: 'italic' }
                        },
                        ticks: { display: false, min: 0, max: 100, stepSize: 20 }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: '#fff', font: { size: 13, family: "'Inter', sans-serif", style: 'italic' }, usePointStyle: true, padding: 20 },
                        position: 'bottom'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)', titleColor: '#fff', bodyColor: 'rgba(255, 255, 255, 0.8)', borderColor: 'rgba(225, 0, 255, 0.4)', borderWidth: 1, padding: 12, displayColors: true, usePointStyle: true, boxPadding: 4
                    }
                }
            }
        });
    }

    // Animar los contadores de texto
    const counters = section.querySelectorAll('.animate-counter');
    counters.forEach(counter => {
        const target = +counter.getAttribute('data-target');
        const duration = 1500; // duración en ms (1.5 segundos)
        let start = 0;
        const increment = target / (duration / 16); // aprox 60fps

        if (target === 0) return;

        const updateCounter = () => {
            start += increment;
            if (start >= target) {
                counter.textContent = target;
            } else {
                counter.textContent = Math.floor(start);
                requestAnimationFrame(updateCounter);
            }
        };

        setTimeout(() => {
            requestAnimationFrame(updateCounter);
        }, 100);
    });
}
