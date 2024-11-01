const apiUrl = 'http://localhost:8000';

// Función para conectar con Facebook Messenger
async function connectFacebook() {
    const apiKey = document.getElementById('facebookApiKeyInput').value;
    if (!apiKey) {
        alert('Por favor, ingrese un API Key válido.');
        return;
    }

    try {
        const response = await fetch(`${apiUrl}/facebook/connect/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });
        const result = await response.json();
        document.getElementById('facebookConnectionStatus').innerText = result.status || result.detail;
    } catch (error) {
        console.error('Error al conectar con Facebook:', error);
    }
}

// Función para subir un PDF
async function uploadPDF() {
    const fileInput = document.getElementById('pdfFileInput');
    const file = fileInput.files[0];
    if (!file) {
        alert('Por favor, seleccione un archivo PDF.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${apiUrl}/pdf/upload/`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        document.getElementById('pdfUploadStatus').innerText = result.message || result.detail;
    } catch (error) {
        console.error('Error al subir el PDF:', error);
    }
}

// Función para hacer preguntas al chatbot
async function askChatbot() {
    const question = document.getElementById('chatbotQuestionInput').value;
    if (!question) {
        alert('Por favor, ingrese una pregunta.');
        return;
    }

    try {
        const response = await fetch(`${apiUrl}/chatbot/ask/?question=${encodeURIComponent(question)}`);
        const result = await response.json();
        document.getElementById('chatbotAnswer').innerText = result.answer;
    } catch (error) {
        console.error('Error al hacer la pregunta al chatbot:', error);
    }
}

// Función para obtener un pedido por ID
async function getOrderById() {
    const orderId = document.getElementById('orderIdInput').value;
    if (!orderId) {
        alert('Por favor, ingrese un ID válido.');
        return;
    }

    try {
        const response = await fetch(`${apiUrl}/orders/${orderId}`);
        const order = await response.json();
        document.getElementById('orderByIdResult').innerHTML = `
            <p><strong>Pedido ID:</strong> ${order.id}</p>
            <p><strong>Teléfono:</strong> ${order.phone}</p>
            <p><strong>Email:</strong> ${order.email}</p>
            <p><strong>Dirección:</strong> ${order.address}</p>
        `;
    } catch (error) {
        console.error('Error al obtener el pedido:', error);
    }
}

// Función para obtener todos los pedidos
async function getAllOrders() {
    try {
        const response = await fetch(`${apiUrl}/orders/`);
        const orders = await response.json();
        let output = '';
        orders.forEach(order => {
            output += `
                <p><strong>Pedido ID:</strong> ${order.id}</p>
                <p><strong>Teléfono:</strong> ${order.phone}</p>
                <p><strong>Email:</strong> ${order.email}</p>
                <p><strong>Dirección:</strong> ${order.address}</p>
                <hr>
            `;
        });
        document.getElementById('allOrdersResult').innerHTML = output || '<p>No hay pedidos disponibles.</p>';
    } catch (error) {
        console.error('Error al obtener los pedidos:', error);
    }
}

// Función para obtener todos los productos
async function getAllProducts() {
    try {
        const response = await fetch(`${apiUrl}/products/`);
        const products = await response.json();
        let output = '';
        products.forEach(product => {
            output += `
                <p><strong>Producto ID:</strong> ${product.id}</p>
                <p><strong>Nombre:</strong> ${product.name}</p>
                <p><strong>Precio:</strong> $${product.price}</p>
                <p><strong>Descripción:</strong> ${product.description || 'N/A'}</p>
                <hr>
            `;
        });
        document.getElementById('allProductsResult').innerHTML = output || '<p>No hay productos disponibles.</p>';
    } catch (error) {
        console.error('Error al obtener los productos:', error);
    }
}
