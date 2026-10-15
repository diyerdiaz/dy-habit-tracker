// Métodos de estudio: modales de crear/editar/eliminar y tablero Kanban.

document.addEventListener('DOMContentLoaded', () => {
    const modal = (id) => bootstrap.Modal.getOrCreateInstance(document.getElementById(id));

    // ── Modal de método (crear / editar) ──
    const metodoForm = document.getElementById('metodoForm');

    function abrirMetodo(boton) {
        const editando = !!boton;
        metodoForm.action = editando ? boton.dataset.url : metodoForm.dataset.crear;
        document.getElementById('metodoModalTitulo').textContent = editando ? 'Editar método' : 'Nuevo método';
        document.getElementById('metodoSubmit').textContent = editando ? 'Actualizar método' : 'Guardar método';
        document.getElementById('metodoNombre').value = editando ? boton.dataset.nombre : '';
        document.getElementById('metodoDescripcion').value = editando ? boton.dataset.descripcion : '';
        marcarRadio('icono', editando ? boton.dataset.icono : null);
        marcarRadio('color', editando ? boton.dataset.color : null);
        modal('metodoModal').show();
    }

    function marcarRadio(nombre, valor) {
        const radios = metodoForm.querySelectorAll(`input[name="${nombre}"]`);
        const elegido = [...radios].find(r => r.value === valor) || radios[0];
        if (elegido) elegido.checked = true;
    }

    // ── Modal de tarjeta (crear / editar) ──
    const tarjetaForm = document.getElementById('tarjetaForm');

    function abrirTarjeta(boton, columna) {
        const editando = boton.dataset.accion === 'editar-tarjeta';
        tarjetaForm.action = editando ? boton.dataset.url : tarjetaForm.dataset.crear;
        document.getElementById('tarjetaModalTitulo').textContent = editando ? 'Editar tarjeta' : 'Nueva tarjeta';
        document.getElementById('tarjetaSubmit').textContent = editando ? 'Actualizar tarjeta' : 'Guardar tarjeta';
        document.getElementById('tarjetaTitulo').value = editando ? boton.dataset.titulo : '';
        document.getElementById('tarjetaDescripcion').value = editando ? boton.dataset.descripcion : '';
        document.getElementById('tarjetaColumna').value = columna || 'pendiente';
        modal('tarjetaModal').show();
    }

    // ── Confirmación de eliminar (método o tarjeta) ──
    function abrirEliminar(boton) {
        document.getElementById('eliminarForm').action = boton.dataset.url;
        document.getElementById('eliminarNombre').textContent = boton.dataset.nombre;
        document.getElementById('eliminarAviso').textContent = boton.dataset.aviso || '';
        modal('eliminarModal').show();
    }

    // ── Subir apuntes a una tarjeta terminada ──
    const apuntesForm = document.getElementById('apuntesForm');
    const apuntesInput = document.getElementById('apuntesArchivos');
    const apuntesError = document.getElementById('apuntesError');
    const apuntesElegidos = document.getElementById('apuntesElegidos');
    const textoZona = apuntesElegidos ? apuntesElegidos.textContent : '';

    function abrirApuntes(boton) {
        apuntesForm.action = boton.dataset.url;
        apuntesForm.reset();
        apuntesError.hidden = true;
        apuntesElegidos.textContent = textoZona;
        document.getElementById('apuntesTarjeta').textContent = boton.dataset.titulo;
        modal('apuntesModal').show();
    }

    if (apuntesForm) {
        const maxBytes = Number(apuntesForm.dataset.maxMb) * 1024 * 1024;
        const mostrarElegidos = () => {
            const n = apuntesInput.files.length;
            apuntesElegidos.textContent = n === 0 ? textoZona
                : n === 1 ? apuntesInput.files[0].name : `${n} archivos elegidos`;
        };
        apuntesInput.addEventListener('change', mostrarElegidos);

        // Soltar archivos sobre la zona
        const zona = apuntesForm.querySelector('.apuntes-zona');
        zona.addEventListener('dragover', (e) => { e.preventDefault(); zona.classList.add('sobre'); });
        zona.addEventListener('dragleave', () => zona.classList.remove('sobre'));
        zona.addEventListener('drop', (e) => {
            e.preventDefault();
            zona.classList.remove('sobre');
            apuntesInput.files = e.dataTransfer.files;
            mostrarElegidos();
        });

        apuntesForm.addEventListener('submit', (e) => {
            const total = [...apuntesInput.files].reduce((suma, f) => suma + f.size, 0);
            if (total > maxBytes) {
                e.preventDefault();
                apuntesError.textContent = `Los archivos pesan ${(total / 1048576).toFixed(1)} MB. El máximo es ${apuntesForm.dataset.maxMb} MB.`;
                apuntesError.hidden = false;
            }
        });
    }

    document.addEventListener('click', (e) => {
        const boton = e.target.closest('[data-accion]');
        if (!boton) return;
        switch (boton.dataset.accion) {
            case 'nuevo-metodo':   abrirMetodo(null); break;
            case 'editar-metodo':  abrirMetodo(boton); break;
            case 'nueva-tarjeta':  abrirTarjeta(boton, boton.dataset.columna); break;
            case 'editar-tarjeta': abrirTarjeta(boton); break;
            case 'eliminar':       abrirEliminar(boton); break;
            case 'mover':          moverConFlecha(boton); break;
            case 'subir-apuntes':  abrirApuntes(boton); break;
        }
    });

    // ── Tablero Kanban ──
    const kanban = document.getElementById('kanban');
    if (!kanban) return;

    const columnas = [...kanban.querySelectorAll('.kanban-columna')].map(c => c.dataset.columna);
    let arrastrada = null;

    function listaDe(columna) {
        return kanban.querySelector(`.kanban-lista[data-columna="${columna}"]`);
    }

    function actualizarContadores() {
        columnas.forEach(col => {
            kanban.querySelector(`[data-contador="${col}"]`).textContent =
                listaDe(col).querySelectorAll('.kanban-tarjeta').length;
        });
    }

    function guardarPosicion(tarjeta) {
        const lista = tarjeta.closest('.kanban-lista');
        const orden = [...lista.querySelectorAll('.kanban-tarjeta')].map(t => t.dataset.id);
        actualizarContadores();
        fetch(tarjeta.dataset.moverUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ columna: lista.dataset.columna, orden }),
        })
            .then(res => res.json())
            .then(data => { if (!data.success) throw new Error(); })
            .catch(() => {
                alert('No se pudo mover la tarjeta. Se recargará el tablero.');
                location.reload();
            });
    }

    function moverConFlecha(boton) {
        const tarjeta = boton.closest('.kanban-tarjeta');
        const actual = columnas.indexOf(tarjeta.closest('.kanban-lista').dataset.columna);
        const destino = columnas[actual + Number(boton.dataset.direccion)];
        if (!destino) return;
        listaDe(destino).appendChild(tarjeta);
        guardarPosicion(tarjeta);
    }

    // Arrastrar y soltar
    kanban.addEventListener('dragstart', (e) => {
        const tarjeta = e.target.closest('.kanban-tarjeta');
        if (!tarjeta) return;
        arrastrada = tarjeta;
        tarjeta.classList.add('arrastrando');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', tarjeta.dataset.id);
    });

    kanban.addEventListener('dragend', () => {
        if (arrastrada) arrastrada.classList.remove('arrastrando');
        kanban.querySelectorAll('.kanban-lista').forEach(l => l.classList.remove('sobre'));
        arrastrada = null;
    });

    kanban.querySelectorAll('.kanban-lista').forEach(lista => {
        lista.addEventListener('dragover', (e) => {
            if (!arrastrada) return;
            e.preventDefault();
            lista.classList.add('sobre');
            // Inserta antes de la primera tarjeta cuyo centro esté por debajo del cursor
            const siguiente = [...lista.querySelectorAll('.kanban-tarjeta:not(.arrastrando)')]
                .find(t => e.clientY < t.getBoundingClientRect().top + t.offsetHeight / 2);
            lista.insertBefore(arrastrada, siguiente || null);
        });
        lista.addEventListener('dragleave', (e) => {
            if (!lista.contains(e.relatedTarget)) lista.classList.remove('sobre');
        });
        lista.addEventListener('drop', (e) => {
            e.preventDefault();
            lista.classList.remove('sobre');
            if (arrastrada) guardarPosicion(arrastrada);
        });
    });
});
