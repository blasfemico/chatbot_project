// frontend/script.js

// Conectar a una cuenta de Facebook usando la API Key
async function connectFacebook() {
    const apiKey = document.getElementById('facebook-api-key').value;
    const response = await fetch('/facebook/connect/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
    });
    
    const result = await response.json();
    document.getElementById('facebook-connection-status').innerText = result.status || "Error al conectar";
}

// Subir PDF de preguntas y respuestas
async function uploadPDF() {
    const fileInput = document.getElementById('pdf-file');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const response = await fetch('/pdf/upload/', {
        method: 'POST',
        body: formData
    });

    const result = await response.json();
    document.getElementById('pdf-upload-status').innerText = result.message || "Error al subir PDF";
}

// Cargar y actualizar la lista de pedidos
async function loadOrders() {
    const response = await fetch('/orders/');
    const orders = await response.json();

    const orderList = document.getElementById('order-list');
    orderList.innerHTML = '';
    orders.forEach(order => {
        const listItem = document.createElement('li');
        listItem.textContent = `Teléfono: ${order.phone}, Email: ${order.email}, Dirección: ${order.address}`;
        orderList.appendChild(listItem);
    });
}

// Conectar a WebSocket para recibir actualizaciones en tiempo real de mensajes
function connectWebSocket() {
    const ws = new WebSocket("ws://localhost:8000/ws/messenger");
    ws.onmessage = (event) => {
        const messageData = JSON.parse(event.data);
        console.log("Mensaje recibido:", messageData);
    };
    ws.onclose = () => console.log("Conexión cerrada");
}

// Inicialización de funciones al cargar la página
document.addEventListener("DOMContentLoaded", () => {
    loadOrders();
    connectWebSocket();
});
