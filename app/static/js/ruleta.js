function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
}

// ----- DATA -----
const castigos_data = window.CASTIGOS_DATA || [];

// ----- FLIP CARD LOGIC -----
const flipCardInner = document.getElementById('flipCardInner');
const obtenerBtn = document.getElementById('obtenerCastigoBtn');
const completadoBtn = document.getElementById('completadoBtn');
const stampOverlay = document.getElementById('stampOverlay');
const stampSeal = document.getElementById('stampSeal');
let currentCastigo = null;

function pickRandom() {
    if (castigos_data.length === 0) return null;
    return castigos_data[Math.floor(Math.random() * castigos_data.length)];
}
function resetCard() {
    flipCardInner.classList.remove('flipped', 'stamp-active');
    stampOverlay.style.display = 'none';
    stampSeal.style.transform = 'scale(0) rotate(-15deg)';
    stampSeal.style.opacity = '0';
    completadoBtn.disabled = false;
    completadoBtn.style.opacity = '1';
    completadoBtn.style.pointerEvents = 'auto';
    const backContent = document.getElementById('backContent');
    if (backContent) {
        backContent.style.transition = 'none';
        backContent.style.opacity = '1';
        backContent.style.visibility = 'visible';
    }
}
obtenerBtn.addEventListener('click', function() {
    if (castigos_data.length === 0) {
        alert('No tienes castigos registrados. ¡Agrega castigos primero!');
        return;
    }
    resetCard();
    currentCastigo = pickRandom();
    document.getElementById('backNombre').textContent = currentCastigo.castigoName;
    document.getElementById('backDesc').textContent = currentCastigo.castigoDesc || 'Sin descripción';
    document.getElementById('backCategoria').textContent = currentCastigo.castigoCategory;
    document.getElementById('backFrecuencia').textContent = currentCastigo.castigoState;
    requestAnimationFrame(() => { flipCardInner.classList.add('flipped'); });
});
completadoBtn.addEventListener('click', function() {
    if (this.disabled || !currentCastigo) return;
    this.disabled = true;
    this.style.opacity = '0.5';
    this.style.pointerEvents = 'none';
    stampOverlay.style.display = 'flex';

    const backContent = document.getElementById('backContent');
    if (backContent) {
        backContent.style.transition = 'opacity 0.3s ease, visibility 0.3s ease';
        backContent.style.opacity = '0';
        backContent.style.visibility = 'hidden';
    }

    requestAnimationFrame(() => {
        stampSeal.style.transform = 'scale(1) rotate(-8deg)';
        stampSeal.style.opacity = '1';
    });
    flipCardInner.classList.remove('stamp-active');
    void flipCardInner.offsetWidth;
    flipCardInner.classList.add('stamp-active');

    fetch('/menu/castigo/' + currentCastigo.idCastigo + '/completar', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const idx = castigos_data.findIndex(c => c.idCastigo === currentCastigo.idCastigo);
                if (idx !== -1) castigos_data[idx].castigoState = 'Completado';
                currentCastigo.castigoState = 'Completado';
                setTimeout(() => location.reload(), 1500);
            }
        })
        .catch(() => {});
});

// ----- STATUS MAPPING -----
function mapStatus(state) {
    if (state === 'Activo') return 'Pendiente';
    if (state === 'Pausado') return 'En progreso';
    if (state === 'Completado') return 'Completado';
    return state;
}

// ----- STAT CARDS (based on real castigos) -----
function updateStats() {
    let pend = 0, comp = 0;
    castigos_data.forEach(c => {
        if (c.castigoState === 'Pendiente') pend++;
        else if (c.castigoState === 'Completado') comp++;
    });
    document.getElementById('countPendientes').textContent = pend;
    document.getElementById('countCompletados').textContent = comp;
}
updateStats();

// ----- CATEGORIES DROPDOWN (from castigos) -----
const cats = [...new Set(castigos_data.map(c => c.castigoCategory))];
const catSelect = document.getElementById('categoryFilter');
cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    opt.style.background = temaColor('oscuro-2');
    catSelect.appendChild(opt);
});

// ----- LIST RENDERING (Castigos registrados) -----
const listEl = document.getElementById('castigosList');
const noResults = document.getElementById('noResultsMsg');

function renderList(filtered) {
    listEl.innerHTML = '';
    if (filtered.length === 0) {
        noResults.style.display = 'block';
        return;
    }
    noResults.style.display = 'none';
    filtered.forEach(c => {
        const status = c.castigoState || 'Pendiente';
        const statusColors = {
            'Pendiente':   { bg: 'rgba(255,102,102,0.15)', border: 'rgba(255,102,102,0.3)', text: '#ff6666' },
            'En progreso': { bg: 'rgba(255,193,7,0.15)',   border: 'rgba(255,193,7,0.3)',   text: '#ffc107' },
            'Completado':  { bg: 'rgba(0,255,171,0.15)',   border: 'rgba(0,255,171,0.3)',   text: '#00ffab' }
        };
        const sc = statusColors[status] || statusColors['Pendiente'];
        const col = document.createElement('div');
        col.className = 'col-12 col-sm-6 col-lg-4 d-flex justify-content-center p-0';
        col.style.maxWidth = '340px';
        col.innerHTML = `
            <div class="castigo-card card shadow-lg border-0 rounded-lg" style="width: 100%; padding: 22px; text-align: center; background: rgba(255,255,255,0.04); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.08); border-radius: 24px;">
                <i class="bi bi-shield-exclamation" style="font-size: 2rem; color: #ff6666; margin-bottom: 10px;"></i>
                <h5 style="color: #fff; font-style: italic; font-weight: 600; margin: 0 0 4px 0; font-size: 1.05rem;">${escapeHtml(c.castigoName)}</h5>
                <p style="color: rgba(255,255,255,0.45); font-size: 0.8rem; margin: 0 0 10px 0; font-style: italic;">${escapeHtml(c.castigoDesc || 'Sin descripción')}</p>
                <div style="margin-bottom: 8px;">
                    <span class="badge rounded-pill" style="background: rgba(255,102,102,0.2); border: 1px solid rgba(255,102,102,0.3); font-style: normal; font-size: 0.7rem; padding: 3px 10px; color: #ff6666;">${escapeHtml(c.castigoCategory)}</span>
                </div>
                <span class="badge rounded-pill" style="background: ${sc.bg}; border: 1px solid ${sc.border}; font-style: normal; font-size: 0.75rem; padding: 4px 14px; color: ${sc.text};">${escapeHtml(status)}</span>
            </div>
        `;
        listEl.appendChild(col);
    });
}

// ----- FILTER LOGIC -----
let currentStatus = 'all';
let currentSearch = '';
let currentDate = 'all';
let currentCategory = 'all';

function getFiltered() {
    return castigos_data.filter(c => {
        const s = c.castigoState || 'Pendiente';
        if (currentStatus !== 'all' && s !== currentStatus) return false;
        if (currentCategory !== 'all' && c.castigoCategory !== currentCategory) return false;
        if (currentSearch && !c.castigoName.toLowerCase().includes(currentSearch.toLowerCase())) return false;
        if (currentDate !== 'all') {
            const d = new Date(c.createdAt);
            const now = new Date();
            if (currentDate === 'today' && d.toDateString() !== now.toDateString()) return false;
            if (currentDate === 'week') {
                const weekStart = new Date(now);
                weekStart.setDate(now.getDate() - now.getDay());
                weekStart.setHours(0,0,0,0);
                if (d < weekStart) return false;
            }
            if (currentDate === 'month' && (d.getMonth() !== now.getMonth() || d.getFullYear() !== now.getFullYear())) return false;
        }
        return true;
    });
}

function applyFilters() {
    renderList(getFiltered());
}

// Search
document.getElementById('searchInput').addEventListener('input', function() {
    currentSearch = this.value;
    applyFilters();
});
// Date
document.getElementById('dateFilter').addEventListener('change', function() {
    currentDate = this.value;
    applyFilters();
});
// Category
document.getElementById('categoryFilter').addEventListener('change', function() {
    currentCategory = this.value;
    applyFilters();
});
// Status badges
document.querySelectorAll('.filter-badge').forEach(b => {
    b.addEventListener('click', function() {
        document.querySelectorAll('.filter-badge').forEach(x => x.classList.remove('active-filter'));
        this.classList.add('active-filter');
        currentStatus = this.getAttribute('data-status');
        applyFilters();
    });
});

// Initial render
applyFilters();

// Toggle History Section
const toggleHistoryBtn = document.getElementById('toggleHistoryBtn');
const historySection = document.getElementById('historySection');

toggleHistoryBtn.addEventListener('click', function() {
    if (historySection.style.display === 'none') {
        historySection.style.display = 'block';
        this.innerHTML = '<i class="bi bi-eye-slash"></i> Ocultar Historial de Castigos';
        // Scroll down a bit to show the history
        setTimeout(() => {
            historySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    } else {
        historySection.style.display = 'none';
        this.innerHTML = '<i class="bi bi-clock-history"></i> Mostrar Historial de Castigos';
    }
});
