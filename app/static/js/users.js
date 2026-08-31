document.getElementById('searchInput').addEventListener('keyup', function() {
    const searchValue = this.value.toLowerCase();
    const rows = document.querySelectorAll('#userTable tr');
    rows.forEach(row => {
        const userName = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        if (userName.includes(searchValue)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
});

let html5QrcodeScanner;

function onScanSuccess(decodedText, decodedResult) {
    try {
        const jsonObject = JSON.parse(decodedText);
        // Accede a cada propiedad del objeto JSON
        const id = jsonObject.ID;
        const name = jsonObject.Name;
        window.location.href = `/User/detail/${id}`;
    } catch (error) {
        // Si el texto decodificado no es un JSON válido, muestra un error
        console.error("Error al parsear el QR a JSON:", error);
        alert(`Código QR escaneado: ${decodedText}\nNota: El texto no es un JSON válido.`);
    }
}


function onScanFailure(error) {
    console.warn(`Error de escaneo: ${error}`);
}

const qrReaderModal = document.getElementById('qrReaderModal');

qrReaderModal.addEventListener('shown.bs.modal', function () {
    html5QrcodeScanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
});

qrReaderModal.addEventListener('hidden.bs.modal', function () {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear().then(() => {
            console.log("Lector de QR detenido y limpiado.");
        }).catch((error) => {
            console.error("Error al detener el lector de QR: ", error);
        });
    }
});
