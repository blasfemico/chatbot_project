const BASE_URL = "http://localhost:8000";

// Enviar Mensaje al Chatbot
async function sendMessage() {
  const question = document.getElementById("chatMessage").value;
  const apiKey = document.getElementById("facebookApiKey").value;

  try {
    const response = await fetch(`${BASE_URL}/chatbot/ask/?question=${encodeURIComponent(question)}&api_key=${apiKey}`, {
      method: "POST",
      headers: { "Accept": "application/json" }
    });

    if (response.ok) {
      const chatbotData = await response.json();
      document.getElementById("chatResponse").textContent = chatbotData.respuesta;
    } else {
      throw new Error("Error al obtener respuesta del chatbot");
    }
  } catch (error) {
    console.error("Error en sendMessage:", error);
  }
}

// Subir PDF
async function uploadPDF() {
  const pdfUpload = document.getElementById("pdfUpload").files[0];
  const formData = new FormData();
  formData.append("file", pdfUpload);

  try {
    const response = await fetch(`${BASE_URL}/pdf/upload/`, {
      method: "POST",
      body: formData
    });

    if (response.ok) {
      document.getElementById("pdfStatus").textContent = "PDF cargado correctamente";
    } else {
      throw new Error("Error al cargar el PDF");
    }
  } catch (error) {
    console.error("Error en uploadPDF:", error);
  }
}

// Conectar Cuenta de Facebook
async function addFacebookAccount() {
  const accountName = document.getElementById("facebookName").value;
  const apiKey = document.getElementById("facebookApiKey").value;

  try {
    const response = await fetch(`${BASE_URL}/facebook/connect/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey })
    });

    if (response.ok) {
      alert(`Cuenta de Facebook ${accountName} conectada exitosamente`);
    } else {
      throw new Error("Error al conectar la cuenta de Facebook");
    }
  } catch (error) {
    console.error("Error en addFacebookAccount:", error);
  }
}

// Agregar Producto
async function addProduct() {
  const name = document.getElementById("productName").value;
  const price = parseFloat(document.getElementById("productPrice").value);
  const accountId = document.getElementById("facebookApiKey").value;

  try {
    const response = await fetch(`${BASE_URL}/cuentas/${accountId}/productos/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, price })
    });

    if (response.ok) {
      alert("Producto agregado exitosamente");
      loadProducts(accountId);
    } else {
      throw new Error("Error al agregar el producto");
    }
  } catch (error) {
    console.error("Error al agregar el producto:", error);
  }
}

// Cargar Productos de una Cuenta
async function loadProducts(accountId) {
  try {
    const response = await fetch(`${BASE_URL}/cuentas/${accountId}/productos/`);
    const products = await response.json();
    const productsList = document.getElementById("productsList");
    productsList.innerHTML = "";
    
    products.forEach(product => {
      const productItem = document.createElement("li");
      productItem.textContent = `${product.name} - $${product.price}`;
      
      const deleteButton = document.createElement("button");
      deleteButton.textContent = "Eliminar";
      deleteButton.onclick = () => deleteProduct(accountId, product.id);
      
      productItem.appendChild(deleteButton);
      productsList.appendChild(productItem);
    });
  } catch (error) {
    console.error("Error al cargar los productos:", error);
  }
}

// Eliminar Producto
async function deleteProduct(accountId, productId) {
  try {
    const response = await fetch(`${BASE_URL}/cuentas/${accountId}/productos/${productId}`, {
      method: "DELETE"
    });
    if (response.ok) {
      alert("Producto eliminado exitosamente");
      loadProducts(accountId);
    } else {
      throw new Error("Error al eliminar el producto");
    }
  } catch (error) {
    console.error("Error al eliminar el producto:", error);
  }
}
