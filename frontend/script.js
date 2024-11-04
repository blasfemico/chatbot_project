document.addEventListener('DOMContentLoaded', () => {
    // Agregar Ciudad y Producto
    document.getElementById('add-city').addEventListener('click', () => {
        const cityName = prompt("Ingrese el nombre de la nueva ciudad:");
        if (cityName) {
            fetch('/cities/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: cityName })
            })
            .then(response => response.json())
            .then(data => {
                loadCities(); // Actualizar lista de ciudades
            })
            .catch(error => console.error("Error al agregar ciudad:", error));
        }
    });

    // Cargar lista de ciudades y productos
    function loadCities() {
        fetch('/cities/')
        .then(response => response.json())
        .then(cities => {
            const cityList = document.getElementById('city-list');
            cityList.innerHTML = '';
            cities.forEach(city => {
                const cityDiv = document.createElement('div');
                cityDiv.classList.add('city');
                cityDiv.innerHTML = `
                    <h3>${city.name} <button onclick="addProduct(${city.id})">+</button></h3>
                    <div id="products-${city.id}" class="product-list"></div>
                `;
                cityList.appendChild(cityDiv);
                loadProducts(city.id);
            });
        })
        .catch(error => console.error("Error al cargar ciudades:", error));
    }

    function addProduct(cityId) {
        const productName = prompt("Ingrese el nombre del producto:");
        const productPrice = prompt("Ingrese el precio del producto:");
        if (productName && productPrice) {
            fetch(`/cities/${cityId}/products/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: productName, price: parseFloat(productPrice) })
            })
            .then(() => loadProducts(cityId))
            .catch(error => console.error("Error al agregar producto:", error));
        }
    }

    function loadProducts(cityId) {
        fetch(`/cities/${cityId}/products/`)
        .then(response => response.json())
        .then(products => {
            const productList = document.getElementById(`products-${cityId}`);
            productList.innerHTML = '';
            products.forEach(product => {
                const productDiv = document.createElement('div');
                productDiv.textContent = `${product.name} - $${product.price}`;
                productList.appendChild(productDiv);
            });
        });
    }

    // Prueba del Chatbot
    document.getElementById('send-chat').addEventListener('click', () => {
        const message = document.getElementById('chat-input').value;
        fetch('/chatbot/ask/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        })
        .then(response => response.json())
        .then(data => {
            const chatWindow = document.getElementById('chat-window');
            chatWindow.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
            document.getElementById('chat-input').value = '';
        })
        .catch(error => console.error("Error en la comunicación con el chatbot:", error));
    });

    // Guardar el Access Token de Facebook
    document.getElementById('save-token').addEventListener('click', () => {
        const token = document.getElementById('fb-token').value;
        fetch('/facebook/token/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token })
        })
        .then(() => alert("Token guardado correctamente"))
        .catch(error => console.error("Error al guardar token:", error));
    });

    // Subir PDF
    document.getElementById('upload-button').addEventListener('click', () => {
        const fileInput = document.getElementById('upload-pdf');
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        fetch('/pdfs/upload/', {
            method: 'POST',
            body: formData
        })
        .then(() => loadPDFs())
        .catch(error => console.error("Error al subir PDF:", error));
    });

    function loadPDFs() {
        fetch('/pdfs/')
        .then(response => response.json())
        .then(pdfs => {
            const pdfList = document.getElementById('pdf-list');
            pdfList.innerHTML = '';
            pdfs.forEach(pdf => {
                const pdfDiv = document.createElement('div');
                pdfDiv.textContent = pdf.name;
                pdfList.appendChild(pdfDiv);
            });
        })
        .catch(error => console.error("Error al cargar PDFs:", error));
    }

    // Cargar datos de órdenes
    function loadOrders() {
        fetch('/orders/')
        .then(response => response.json())
        .then(orders => {
            const orderTable = document.getElementById('order-table').querySelector('tbody');
            orderTable.innerHTML = '';
            orders.forEach(order => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${order.date}</td>
                    <td>${order.product_name}</td>
                    <td>${order.customer_name}</td>
                    <td>${order.phone}</td>
                    <td>${order.address}</td>
                    <td>${order.status}</td>
                `;
                orderTable.appendChild(row);
            });
        })
        .catch(error => console.error("Error al cargar órdenes:", error));
    }

    // Inicializar cargas
    loadCities();
    loadPDFs();
    loadOrders();
});
