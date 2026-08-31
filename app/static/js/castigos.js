const ITEMS_PER_PAGE = 5;
let currentPage = 1;
let filteredRows = [];

document.addEventListener("DOMContentLoaded", function() {
    // Sidebar logic
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

    // Intro animation
    const fadeSections = document.querySelectorAll('.fade-in-section');
    const scrollObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                scrollObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    fadeSections.forEach(section => scrollObserver.observe(section));

    // Inicializar Filtros y Paginación
    initFiltersAndPagination();
});

// ── LÓGICA DE FILTROS Y BÚSQUEDA ──
const searchInput = document.getElementById('searchInput');
const filterCategory = document.getElementById('filterCategory');
const filterState = document.getElementById('filterState');
const allRows = Array.from(document.querySelectorAll('.castigo-row'));
const emptyRow = document.getElementById('emptyRow');
const noResultsRow = document.getElementById('noResultsRow');

function initFiltersAndPagination() {
    if(allRows.length > 0 && emptyRow) { emptyRow.style.display = 'none'; }

    searchInput.addEventListener('input', applyFilters);
    filterCategory.addEventListener('change', applyFilters);
    filterState.addEventListener('change', applyFilters);

    applyFilters();
}

function applyFilters() {
    const query = searchInput.value.toLowerCase();
    const category = filterCategory.value.toLowerCase();
    const state = filterState.value.toLowerCase();

    filteredRows = allRows.filter(row => {
        const rowName = row.dataset.name || '';
        const rowDesc = (row.dataset.desc || '').toLowerCase();
        const rowCat = (row.dataset.category || '').toLowerCase();
        const rowState = (row.dataset.state || '').toLowerCase();

        const matchSearch = rowName.includes(query) || rowDesc.includes(query);
        const matchCat = category === '' || rowCat === category;
        const matchState = state === '' || rowState === state;

        return matchSearch && matchCat && matchState;
    });

    currentPage = 1;
    updateTable();
}

function updateTable() {
    allRows.forEach(row => row.style.display = 'none');
    if (noResultsRow) noResultsRow.style.display = 'none';

    if (filteredRows.length === 0 && allRows.length > 0) {
        if (noResultsRow) noResultsRow.style.display = '';
        document.getElementById('paginationControls').innerHTML = '';
        document.getElementById('pageInfo').textContent = 'Mostrando 0 registros';
        return;
    }

    const totalPages = Math.ceil(filteredRows.length / ITEMS_PER_PAGE);
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;

    filteredRows.slice(startIndex, endIndex).forEach(row => row.style.display = '');

    const infoText = `Mostrando ${filteredRows.length === 0 ? 0 : startIndex + 1} - ${Math.min(endIndex, filteredRows.length)} de ${filteredRows.length} registros`;
    document.getElementById('pageInfo').textContent = infoText;

    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    const ul = document.getElementById('paginationControls');
    ul.innerHTML = '';

    if (totalPages <= 1) return;

    ul.innerHTML += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link glass-input" href="#" onclick="goToPage(${currentPage - 1}, event)">Anterior</a>
    </li>`;

    for (let i = 1; i <= totalPages; i++) {
        ul.innerHTML += `<li class="page-item ${currentPage === i ? 'active' : ''}">
            <a class="page-link glass-input" href="#" onclick="goToPage(${i}, event)" ${currentPage === i ? 'style="background: #9b59b6 !important; border-color: #9b59b6 !important;"' : ''}>${i}</a>
        </li>`;
    }

    ul.innerHTML += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link glass-input" href="#" onclick="goToPage(${currentPage + 1}, event)">Siguiente</a>
    </li>`;
}

function goToPage(page, event) {
    if(event) event.preventDefault();
    const totalPages = Math.ceil(filteredRows.length / ITEMS_PER_PAGE);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        updateTable();
    }
}

// ── LÓGICA DE MODALES ──

function openEditModal(id, name, desc, freq, category) {
    document.getElementById('editForm').action = `/castigo/${id}/edit`;
    document.getElementById('editName').value = name;
    document.getElementById('editDesc').value = desc !== 'None' ? desc : '';
    document.getElementById('editCategory').value = freq;
    document.getElementById('editCategory').value = category;
    var modal = new bootstrap.Modal(document.getElementById('editModal'));
    modal.show();
}

function openStateModal(id, state, name) {
    document.getElementById('stateForm').action = `/castigo/${id}/state`;
    document.getElementById('stateSelect').value = state;
    document.getElementById('stateCastigoName').textContent = name;
    var modal = new bootstrap.Modal(document.getElementById('stateModal'));
    modal.show();
}

function openDeleteModal(id, name) {
    document.getElementById('deleteForm').action = `/castigo/${id}/delete`;
    document.getElementById('delCastigoName').textContent = name;
    var modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

function openViewModal(id) {
    fetch(`/castigo/${id}/json`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('viewName').textContent = data.castigoName;
            document.getElementById('viewState').textContent = data.castigoState;
            document.getElementById('viewCategory').textContent = data.castigoCategory.charAt(0).toUpperCase() + data.castigoCategory.slice(1);
            document.getElementById('viewCategory').textContent = data.castigoCategory.charAt(0).toUpperCase() + data.castigoCategory.slice(1);
            document.getElementById('viewDesc').textContent = data.castigoDesc || 'No se proporcionó descripción.';
            document.getElementById('viewDate').textContent = data.createdAt;

            const stateBadge = document.getElementById('viewState');
            stateBadge.className = 'badge rounded-pill mt-1 ' +
                (data.castigoState === 'Activo' ? 'bg-success' :
                data.castigoState === 'Pausado' ? 'bg-warning text-dark' : 'bg-info');

            var modal = new bootstrap.Modal(document.getElementById('viewModal'));
            modal.show();
        })
        .catch(err => alert("Error cargando los detalles del castigo."));
}
