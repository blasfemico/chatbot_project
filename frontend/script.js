// frontend/script.js

// Conectar a una cuenta de Facebook usando la API Key
async function connectFacebook() {
    const apiKey = document.getElementById('facebook-api-key').value;
    try {
        const response = await fetch('http://localhost:8000/facebook/connect/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ api_key: apiKey })
        });
        const result = await response.json();
        document.getElementById('facebook-connection-status').innerText = result.status || "Error al conectar";
    } catch (error) {
        console.error('Error en la conexión:', error);
        document.getElementById('facebook-connection-status').innerText = "Error al conectar";
    }
}

// Subir PDF de preguntas y respuestas
async function uploadPDF() {
    const fileInput = document.getElementById('pdf-file');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('http://localhost:8000/pdf/upload/', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        document.getElementById('pdf-upload-status').innerText = result.message || "Error al subir PDF";
    } catch (error) {
        console.error('Error al subir PDF:', error);
        document.getElementById('pdf-upload-status').innerText = "Error al subir PDF";
    }
}

// Realizar una pregunta al chatbot
async function askQuestion() {
    const question = document.getElementById('question-input').value;
    try {
        const response = await fetch('http://localhost:8000/chatbot/ask/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: question })
        });
        const result = await response.json();
        document.getElementById('chatbot-response').innerText = result.answer || "Lo siento, no tengo una respuesta para esa pregunta";
    } catch (error) {
        console.error('Error al preguntar al chatbot:', error);
        document.getElementById('chatbot-response').innerText = "Error al obtener respuesta del chatbot";
    }
}
