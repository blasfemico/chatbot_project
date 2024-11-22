const backendUrl = "https://kokomibot.up.railway.app/";

async function loadSection(section) {
    let content = document.getElementById("content");
    switch (section) {
        case "cuentas":
            content.innerHTML = `
                <h2>Gestionar Cuentas</h2>
                <button onclick="fetchCuentas()">Ver Cuentas Activas</button>
                <div id="cuentas-list"></div>
                <h3>Crear Nueva Cuenta</h3>
                <form onsubmit="createCuenta(event)">
                    <input type="text" id="pageid" placeholder="Page ID" required>
                    <input type="text" id="nombreCuenta" placeholder="Nombre de la Cuenta" required>
                    <button type="submit">Crear Cuenta</button>
                </form>
            `;
            break;
        case "ciudades":
            content.innerHTML = `
                <h2>Gestionar Ciudades</h2>
                <button onclick="fetchCiudades()">Ver Ciudades</button>
                <div id="ciudades-list"></div>
                <h3>Ver Productos de una Ciudad</h3>
                <input type="number" id="ciudadId" placeholder="ID de la Ciudad" required>
                <button onclick="fetchProductosPorCiudad()">Ver Productos</button>
                <div id="productos-ciudad-list"></div>
                <h3>Agregar Producto a una Ciudad</h3>
                <form onsubmit="addProductoToCiudad(event)">
                    <input type="number" id="ciudadIdAgregar" placeholder="ID de la Ciudad" required>
                    <input type="text" id="nombreProductoCiudad" placeholder="Nombre del Producto" required>
                    <button type="submit">Agregar Producto</button>
                </form>
                <h3>Crear Nueva Ciudad</h3>
                <form onsubmit="createCiudad(event)">
                    <input type="text" id="nombreCiudad" placeholder="Nombre de la Ciudad" required>
                    <button type="submit">Crear Ciudad</button>
                </form>
            `;
            break;
        case "productos":
            content.innerHTML = `
                <h2>Gestionar Productos</h2>
                <input type="number" id="cuentaId" placeholder="ID de la Cuenta" required>
                <button onclick="fetchProductos()">Ver Productos</button>
                <div id="productos-list"></div>
                <h3>Crear Productos</h3>
                <form onsubmit="createProductos(event)">
                    <textarea id="productosData" placeholder="ID de la Cuenta, Nombre del Producto, Precio por línea" required></textarea>
                    <button type="submit">Crear Productos</button>
                </form>
            `;
            break;
        case "faqs":
            content.innerHTML = `
                <h2>Gestionar FAQs</h2>
                <button onclick="fetchFaqs()">Ver FAQs</button>
                <div id="faqs-list"></div>
                <h3>Crear FAQs en Bloque</h3>
                <form onsubmit="createFaqsBulk(event)">
                    <textarea id="faqsData" placeholder="Pregunta, Respuesta por línea" required></textarea>
                    <button type="submit">Crear FAQs</button>
                </form>
            `;
             break;
            
        case "ordenes":
            content.innerHTML = `
                <h2>Gestionar Órdenes</h2>
                <button onclick="fetchOrders()">Ver Todas las Órdenes</button>
                <input type="number" id="orderId" placeholder="ID de la Orden" required>
                <button onclick="fetchOrderById()">Ver Orden por ID</button>
                <div id="orders-list"></div>
                <div id="single-order"></div>
                <h3>Exportar Órdenes a Excel</h3>
                <form onsubmit="exportOrdersToExcel(event)">
                    <input type="text" id="excelPath" placeholder="Ruta de Guardado del Archivo Excel" required>
                    <button type="submit">Exportar y Descargar</button>
                </form>
                <div id="excel-download-link"></div>
            `;
            break;
        case "chatbot":
            content.innerHTML = `
                <h2>Preguntar al Chatbot</h2>
                <form onsubmit="askChatbot(event)">
                    <input type="text" id="chatbotQuestion" placeholder="Escribe tu pregunta" required>
                    <input type="number" id="chatbotCuentaId" placeholder="ID de la Cuenta" required>
                    <button type="submit">Enviar Pregunta</button>
                </form>
                <div id="chatbot-response"></div>
            `;
            break;
        case "apikeys":
            content.innerHTML = `
                <h2>Gestionar API Keys</h2>
                <button onclick="fetchApiKeys()">Ver API Keys</button>
                <div id="apikeys-list"></div>
                <h3>Agregar Nueva API Key</h3>
                <form onsubmit="createApiKey(event)">
                    <input type="text" id="nombreApiKey" placeholder="Nombre de la Cuenta" required>
                    <input type="text" id="apiKeyValue" placeholder="Valor de la API Key" required>
                    <button type="submit">Agregar API Key</button>
                </form>
            `;
            break;
            
    }
}

async function fetchCuentas() {
    const response = await fetch(`${backendUrl}accounts/all`);
    const cuentas = await response.json();
    document.getElementById("cuentas-list").innerHTML = cuentas.map(cuenta => `
        <p>${cuenta.nombre} (Page ID: ${cuenta.page_id}) 
            <button onclick="deleteCuenta(${cuenta.id})">Eliminar</button>
        </p>`).join("");
}

async function createCuenta(event) {
    event.preventDefault();
    const pageid = document.getElementById("pageid").value;
    const nombre = document.getElementById("nombreCuenta").value;
    await fetch(`${backendUrl}accounts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page_id: pageid, nombre })
    });
    alert("Cuenta creada con éxito");
    fetchCuentas();
}


async function deleteCuenta(cuentaId) {
    await fetch(`${backendUrl}accounts/${cuentaId}/delete`, { method: 'DELETE' })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }
            alert("Cuenta eliminada con éxito");
            fetchCuentas();
        })
        .catch(error => {
            console.error("Error al eliminar la cuenta:", error);
            alert("No se pudo eliminar la cuenta. Revisa la consola para más detalles.");
        });
}


async function fetchCiudades() {
    try {
        const response = await fetch(`${backendUrl}cities/all/`);
        const data = await response.json();
        const ciudades = data.ciudades;
        if (!Array.isArray(ciudades)) {
            console.error("La respuesta no es una lista:", ciudades);
            document.getElementById("ciudades-list").innerHTML = "<p>Error al cargar ciudades.</p>";
            return;
        }
        document.getElementById("ciudades-list").innerHTML = ciudades.map(ciudad => `
            <p>ID: ${ciudad.id} - Nombre: ${ciudad.nombre} 
                <button onclick="deleteCiudad(${ciudad.id})">Eliminar</button>
            </p>
        `).join("");
    } catch (error) {
        console.error("Error al cargar ciudades:", error);
        document.getElementById("ciudades-list").innerHTML = "<p>Error al cargar ciudades.</p>";
    }
}



async function fetchProductosPorCiudad() {
    const ciudadId = document.getElementById("ciudadId").value;
    const response = await fetch(`${backendUrl}cities/${ciudadId}/products`);
    const productos = await response.json();
    document.getElementById("productos-ciudad-list").innerHTML = productos.map(producto => `
        <p>${producto.nombre}</p>
    `).join("");
}

async function addProductoToCiudad(event) {
    event.preventDefault();
    const ciudadId = document.getElementById("ciudadIdAgregar").value;
    const nombreProducto = document.getElementById("nombreProductoCiudad").value;
    await fetch(`${backendUrl}cities/${ciudadId}/products`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ productos: [nombreProducto] })
    });
    alert("Producto agregado a la ciudad con éxito");
    fetchProductosPorCiudad();
}

async function createCiudad(event) {
    event.preventDefault();
    const nombre = document.getElementById("nombreCiudad").value;
    await fetch(`${backendUrl}cities/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ nombre })
    });
    alert("Ciudad creada con éxito");
    fetchCiudades();
}

async function deleteCiudad(ciudadId) {
    await fetch(`${backendUrl}cities/${ciudadId}/`, { method: 'DELETE' });
    alert("Ciudad eliminada con éxito");
    fetchCiudades();
}

async function fetchProductos() {
    const cuentaId = document.getElementById("cuentaId").value;
    if (!cuentaId) {
        alert("Por favor, ingresa el ID de la cuenta.");
        return;
    }
    try {
        const response = await fetch(`${backendUrl}accounts/${cuentaId}/products`);
        const productos = await response.json();

        // Asegúrate de que `productos` sea un array y tenga datos válidos
        if (!Array.isArray(productos)) {
            console.error("La respuesta no es una lista de productos:", productos);
            document.getElementById("productos-list").innerHTML = "<p>Error al cargar productos.</p>";
            return;
        }

        // Genera el HTML asegurándote de que cada producto tiene un id válido
        document.getElementById("productos-list").innerHTML = productos
            .map((producto) => {
                if (!producto.id) {
                    console.error("Producto sin ID encontrado:", producto);
                    return `<p>Error: Producto sin ID no se puede eliminar.</p>`;
                }
                return `
                    <p>${producto.producto} - Precio: ${producto.precio}
                        <button onclick="deleteProducto(${producto.id})">Eliminar</button>
                    </p>`;
            })
            .join("");
    } catch (error) {
        console.error("Error al cargar productos:", error);
        document.getElementById("productos-list").innerHTML = "<p>Error al cargar productos.</p>";
    }
}


async function createProductos(event) {
    event.preventDefault();
    const productosData = document.getElementById("productosData").value;
    const productos = productosData.split('\n').map(line => {
        const [cuentaId, nombre, precio] = line.split(',').map(item => item.trim());
        return { cuenta_id: parseInt(cuentaId), nombre, precio: parseFloat(precio) };
    });

    for (const producto of productos) {
        await fetch(`${backendUrl}accounts/${producto.cuenta_id}/products`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ productos: [{ nombre: producto.nombre, precio: producto.precio }] })
        });
    }
    alert("Productos creados con éxito");
    fetchProductos();
}

async function deleteProducto(productoId) {
    await fetch(`${backendUrl}products/${productoId}`, { method: 'DELETE' });
    alert("Producto eliminado con éxito");
    fetchProductos();
}
async function fetchFaqs() {
    const response = await fetch(`${backendUrl}faq/all`);
    const faqs = await response.json();
    document.getElementById("faqs-list").innerHTML = faqs.map(faq => `
        <p>${faq.question}: ${faq.answer}
            <button onclick="deleteFaq(${faq.id})">Eliminar</button>
        </p>
    `).join("");
}

async function createFaqsBulk(event) {
    event.preventDefault();

    const faqsData = document.getElementById("faqsData").value.trim();
    const faqs = faqsData.split('\n').map(line => {
        if (!line.includes(';')) {
            alert("Cada línea debe tener el formato 'pregunta;respuesta'.");
            return null;
        }
        const [question, answer] = line.split(';').map(item => item.trim());
        return { question, answer };
    }).filter(faq => faq !== null); 

    if (faqs.length === 0) {
        alert("Por favor, revisa el formato de las preguntas y respuestas.");
        return;
    }

    try {
        const response = await fetch(`${backendUrl}faq/bulk_add/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(faqs)
        });

        if (response.ok) {
            alert("FAQs creadas con éxito");
            fetchFaqs(); 
        } else {
            alert("Error al crear FAQs. Revisa el formato de entrada.");
        }
    } catch (error) {
        console.error("Error al crear FAQs en bloque:", error);
        alert("Ocurrió un error al procesar la solicitud.");
    }
}

async function deleteFaq(faqId) {
    await fetch(`${backendUrl}faq/delete/${faqId}`, { method: 'DELETE' });
    alert("FAQ eliminada con éxito");
    fetchFaqs();
}

async function fetchOrders() {
    try {
        const response = await fetch(`${backendUrl}orders/all/`);
        if (!response.ok) throw new Error(`Error: ${response.status} ${response.statusText}`);
        const orders = await response.json();

        document.getElementById("orders-list").innerHTML = orders.map(order => `
            <p>Orden ID: ${order.id} - 
               Producto: ${order.producto}, 
               Cantidad: ${order.cantidad_cajas}, 
               Teléfono: ${order.phone || "N/A"}, 
               Email: ${order.email || "N/A"}, 
               Dirección: ${order.address || "N/A"}, 
               Nombre: ${order.nombre || "N/A"}, 
               Apellido: ${order.apellido || "N/A"}, 
               Ad ID: ${order.ad_id || "N/A"}
               <button onclick="deleteOrder(${order.id})">Eliminar</button>
            </p>
        `).join("");
    } catch (error) {
        console.error("Error al cargar órdenes:", error);
        document.getElementById("orders-list").innerHTML = "<p>Error al cargar órdenes.</p>";
    }
}

async function fetchOrderById() {
    const orderId = document.getElementById("orderId").value;
    if (!orderId) {
        alert("Por favor, introduce un ID de orden para ver el detalle.");
        return;
    }

    try {
        const response = await fetch(`${backendUrl}orders/${orderId}`);
        if (!response.ok) {
            document.getElementById("single-order").innerHTML = `<p>Orden con ID ${orderId} no encontrada.</p>`;
            return;
        }

        const order = await response.json();
        document.getElementById("single-order").innerHTML = `
            <h3>Detalles de la Orden ID: ${order.id}</h3>
            <p>Producto: ${order.producto}</p>
            <p>Cantidad: ${order.cantidad_cajas}</p>
            <p>Teléfono: ${order.phone || "N/A"}</p>
            <p>Email: ${order.email || "N/A"}</p>
            <p>Dirección: ${order.address || "N/A"}</p>
            <p>Nombre: ${order.nombre || "N/A"}</p>
            <p>Apellido: ${order.apellido || "N/A"}</p>
            <p>Ad ID: ${order.ad_id || "N/A"}</p>
            <button onclick="deleteOrder(${order.id})">Eliminar esta Orden</button>
        `;
    } catch (error) {
        console.error("Error al cargar la orden:", error);
        document.getElementById("single-order").innerHTML = "<p>Error al cargar la orden.</p>";
    }
}

async function deleteOrder(orderId) {
    await fetch(`${backendUrl}orders/${orderId}`, { method: 'DELETE' });
    alert("Orden eliminada con éxito");
    fetchOrders();
}

async function exportOrdersToExcel(event) {
    event.preventDefault();
    const filePath = document.getElementById("excelPath").value;

    try {
        const response = await fetch(`${backendUrl}orders/export_excel/?file_path=${encodeURIComponent(filePath)}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = filePath.split('/').pop();
        link.innerText = "Descargar Archivo Excel";
        document.getElementById("excel-download-link").innerHTML = "";
        document.getElementById("excel-download-link").appendChild(link);

        alert("Archivo exportado y listo para descargar.");
    } catch (error) {
        console.error("Error al exportar órdenes a Excel:", error);
        document.getElementById("excel-download-link").innerHTML = "<p>Error al exportar el archivo.</p>";
    }
}


async function askChatbot(event) {
    event.preventDefault();
    const question = document.getElementById("chatbotQuestion").value;
    const cuentaId = parseInt(document.getElementById("chatbotCuentaId").value);
    const response = await fetch(`${backendUrl}chatbot/ask/?question=${encodeURIComponent(question)}&cuenta_id=${cuentaId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json();
    document.getElementById("chatbot-response").innerHTML = `
        <p>Respuesta del Chatbot: ${data.respuesta}</p>
    `;
}

async function fetchApiKeys() {
    const response = await fetch(`${backendUrl}apikeys/`);
    const apiKeys = await response.json();
    if (!Array.isArray(apiKeys)) {
        console.error("La respuesta no es una lista:", apiKeys);
        document.getElementById("apikeys-list").innerHTML = "<p>Error al cargar las API Keys.</p>";
        return;
    }
    document.getElementById("apikeys-list").innerHTML = apiKeys.map(key => `
        <p>${key.name}: ${key.key}
            <button onclick="deleteApiKey('${key.name}')">Eliminar</button>
        </p>
    `).join("");
}


async function createApiKey(event) {
    event.preventDefault();
    const name = document.getElementById("nombreApiKey").value;
    const key = document.getElementById("apiKeyValue").value;

    const response = await fetch(`${backendUrl}apikeys/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, key })
    });

    if (response.ok) {
        alert("API Key creada con éxito");
        fetchApiKeys(); 
    } else {
        const errorData = await response.json();
        alert(`Error: ${errorData.detail}`);
    }
}

async function deleteApiKey(name) {
    await fetch(`${backendUrl}apikeys/${name}`, { method: 'DELETE' });
    alert("API Key eliminada con éxito");
    fetchApiKeys();
}
