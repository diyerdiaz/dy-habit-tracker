// ── Sidebar ──
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

// ── Typing Effect ──
document.addEventListener('DOMContentLoaded', () => {
    const titleText = "Estadísticas";
    const el = document.getElementById('typingTitle');
    const cursor = document.getElementById('cursor');
    const desc = document.getElementById('descText');
    let i = 0;
    function type() {
        if (i < titleText.length) {
            el.textContent += titleText.charAt(i++);
            setTimeout(type, 80);
        } else {
            setTimeout(() => cursor.style.display = 'none', 800);
            desc.style.opacity = '1';
            desc.style.transform = 'translateY(0)';
        }
    }
    setTimeout(type, 300);

    // ── Staggered Card Animations ──
    const cards = document.querySelectorAll('.stat-card');
    cards.forEach((card, idx) => {
        setTimeout(() => card.classList.add('visible'), 400 + idx * 120);
    });

    // ── Chart cards animation ──
    const chartCards = document.querySelectorAll('.chart-card');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });
    chartCards.forEach(c => observer.observe(c));

    // Empty state
    const empty = document.getElementById('emptyState');
    if (empty) setTimeout(() => empty.classList.add('visible'), 500);

    // ── Animated counters ──
    const counters = document.querySelectorAll('.animate-counter');
    counters.forEach(counter => {
        const target = +counter.getAttribute('data-target');
        if (target === 0) return;
        const duration = 1500;
        const inc = target / (duration / 16);
        let val = 0;
        function update() {
            val += inc;
            if (val >= target) { counter.textContent = target; }
            else { counter.textContent = Math.floor(val); requestAnimationFrame(update); }
        }
        setTimeout(() => requestAnimationFrame(update), 700);
    });

    if (window.STATS_DATA) {
        // ══════ CHART.JS CHARTS ══════
        const stats = window.STATS_DATA;
        const chartFont = { family: "'Poppins', sans-serif", style: 'italic' };
        const gridColor = 'rgba(255,255,255,0.08)';
        const tickColor = 'rgba(255,255,255,0.5)';

        // ── RADAR ──
        const rCtx = document.getElementById('radarChart').getContext('2d');
        const rGrad = rCtx.createLinearGradient(0, 0, 0, 340);
        rGrad.addColorStop(0, temaRgba('grad-2', 0.35));
        rGrad.addColorStop(1, temaRgba('grad-1', 0.05));

        new Chart(rCtx, {
            type: 'radar',
            data: {
                labels: stats.radar_labels,
                datasets: [{
                    label: 'Hábitos Activos',
                    data: stats.radar_data,
                    backgroundColor: rGrad,
                    borderColor: temaColor('grad-2'),
                    pointBackgroundColor: temaRgba('oscuro', 0.95),
                    pointBorderColor: temaColor('grad-2'),
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: temaColor('grad-2'),
                    borderWidth: 2.5,
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                animation: { duration: 2500, easing: 'easeOutQuint' },
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255,255,255,0.12)' },
                        grid: { color: 'rgba(255,255,255,0.08)', circular: true },
                        pointLabels: { color: 'rgba(255,255,255,0.8)', font: { ...chartFont, size: 12 } },
                        ticks: { display: false },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: { labels: { color: '#fff', font: { ...chartFont, size: 13 }, usePointStyle: true, padding: 20 }, position: 'bottom' },
                    tooltip: { backgroundColor: 'rgba(0,0,0,0.85)', titleColor: '#fff', bodyColor: 'rgba(255,255,255,0.8)', borderColor: temaRgba('grad-2', 0.4), borderWidth: 1, padding: 12 }
                }
            }
        });

        // ── BAR ──
        const bCtx = document.getElementById('barChart').getContext('2d');
        const bGrad = bCtx.createLinearGradient(0, 280, 0, 0);
        bGrad.addColorStop(0, temaRgba('grad-1', 0.8));
        bGrad.addColorStop(1, temaRgba('grad-2', 0.8));

        new Chart(bCtx, {
            type: 'bar',
            data: {
                labels: stats.week_labels,
                datasets: [{
                    label: 'Hábitos Creados',
                    data: stats.week_data,
                    backgroundColor: bGrad,
                    borderColor: temaRgba('grad-2', 0.6),
                    borderWidth: 1,
                    borderRadius: 8,
                    borderSkipped: false,
                    barPercentage: 0.6
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                animation: { duration: 2000, easing: 'easeOutQuint' },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: tickColor, font: { ...chartFont, size: 11 } } },
                    y: { grid: { color: gridColor }, ticks: { color: tickColor, font: { ...chartFont, size: 11 }, stepSize: 1 }, beginAtZero: true }
                },
                plugins: {
                    legend: { labels: { color: '#fff', font: { ...chartFont, size: 13 }, usePointStyle: true, padding: 20 }, position: 'bottom' },
                    tooltip: { backgroundColor: 'rgba(0,0,0,0.85)', titleColor: '#fff', bodyColor: 'rgba(255,255,255,0.8)', borderColor: temaRgba('grad-2', 0.4), borderWidth: 1, padding: 12 }
                }
            }
        });

        // ── LINE ──
        const lCtx = document.getElementById('lineChart').getContext('2d');
        const lGrad = lCtx.createLinearGradient(0, 0, 0, 300);
        lGrad.addColorStop(0, 'rgba(0, 186, 198, 0.4)');
        lGrad.addColorStop(1, 'rgba(0, 255, 171, 0.02)');

        new Chart(lCtx, {
            type: 'line',
            data: {
                labels: stats.line_labels,
                datasets: [{
                    label: '% Cumplimiento',
                    data: stats.line_data,
                    fill: true,
                    backgroundColor: lGrad,
                    borderColor: '#00bac6',
                    pointBackgroundColor: temaRgba('oscuro', 0.95),
                    pointBorderColor: '#00ffab',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#00bac6',
                    borderWidth: 3,
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 9,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                animation: { duration: 2500, easing: 'easeOutQuint' },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: tickColor, font: { ...chartFont, size: 11 } } },
                    y: { grid: { color: gridColor }, ticks: { color: tickColor, font: { ...chartFont, size: 11 }, callback: v => v + '%' }, beginAtZero: true, max: 100 }
                },
                plugins: {
                    legend: { labels: { color: '#fff', font: { ...chartFont, size: 13 }, usePointStyle: true, padding: 20 }, position: 'bottom' },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.85)', titleColor: '#fff', bodyColor: 'rgba(255,255,255,0.8)', borderColor: 'rgba(0,186,198,0.5)', borderWidth: 1, padding: 12,
                        callbacks: { label: ctx => ctx.parsed.y + '% cumplimiento' }
                    }
                }
            }
        });
    }
});
