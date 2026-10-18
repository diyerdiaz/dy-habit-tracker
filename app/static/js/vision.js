// Vision Board: modal para crear / editar metas con vista previa de la imagen
document.addEventListener('DOMContentLoaded', function () {
    var modalEl = document.getElementById('metaModal');
    if (!modalEl) return;
    var modal = new bootstrap.Modal(modalEl);
    var form = document.getElementById('metaForm');
    var inputImagen = document.getElementById('metaImagen');
    var preview = document.getElementById('metaPreview');
    var dropTexto = document.getElementById('metaDropTexto');
    var dropzone = form.querySelector('.vision-dropzone');

    function mostrarPreview(src) {
        if (src) {
            preview.src = src;
            preview.hidden = false;
            dropTexto.hidden = true;
        } else {
            preview.removeAttribute('src');
            preview.hidden = true;
            dropTexto.hidden = false;
        }
    }

    function abrir(datos) {
        form.reset();
        var editando = !!datos;
        form.action = editando ? datos.url : form.dataset.crear;
        // Al editar, la imagen es opcional: si no se elige otra se queda la actual
        inputImagen.required = !editando;
        document.getElementById('metaModalTitulo').textContent = editando ? 'Editar meta' : 'Nueva meta';
        document.getElementById('metaSubmit').textContent = editando ? 'Guardar cambios' : 'Guardar meta';
        document.getElementById('metaTitulo').value = editando ? datos.titulo : '';
        document.getElementById('metaDescripcion').value = editando ? datos.descripcion : '';
        document.getElementById('metaCategoria').value = editando ? datos.categoria : 'personal';
        document.getElementById('metaFecha').value = editando ? datos.fecha : '';
        mostrarPreview(editando ? datos.imagen : null);
        modal.show();
    }

    document.querySelectorAll('#btnNuevaMeta, [data-nueva-meta]').forEach(function (btn) {
        btn.addEventListener('click', function () { abrir(null); });
    });

    document.querySelectorAll('[data-editar]').forEach(function (btn) {
        btn.addEventListener('click', function () { abrir(btn.dataset); });
    });

    inputImagen.addEventListener('change', function () {
        var archivo = inputImagen.files[0];
        if (archivo) mostrarPreview(URL.createObjectURL(archivo));
    });

    // Arrastrar y soltar una imagen sobre el recuadro
    ['dragenter', 'dragover'].forEach(function (evento) {
        dropzone.addEventListener(evento, function (e) {
            e.preventDefault();
            dropzone.classList.add('arrastrando');
        });
    });
    ['dragleave', 'drop'].forEach(function (evento) {
        dropzone.addEventListener(evento, function (e) {
            e.preventDefault();
            dropzone.classList.remove('arrastrando');
        });
    });
    dropzone.addEventListener('drop', function (e) {
        if (e.dataTransfer.files.length) {
            inputImagen.files = e.dataTransfer.files;
            inputImagen.dispatchEvent(new Event('change'));
        }
    });

    // Confirmación antes de eliminar
    var eliminarModal = new bootstrap.Modal(document.getElementById('eliminarModal'));
    document.querySelectorAll('[data-eliminar]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.getElementById('eliminarForm').action = btn.dataset.url;
            document.getElementById('eliminarTitulo').textContent = btn.dataset.titulo;
            eliminarModal.show();
        });
    });
});
