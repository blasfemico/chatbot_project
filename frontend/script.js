const BASE_URL = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", () => {
  loadCities();
  loadChatbotResponse();
});

async function loadCities() {
  try {
    const response = await fetch(`${BASE_URL}/cities/`);
    if (!response.ok) {
      throw new Error("Error al cargar las ciudades");
    }
    const cities = await response.json();
    const citySelect = document.getElementById("citySelect");
    citySelect.innerHTML = "";
    cities.forEach(city => {
      const option = document.createElement("option");
      option.value = city.id;
      option.text = city.name;
      citySelect.add(option);
    });
    citySelect.addEventListener("change", () => {
      loadProducts(citySelect.value);
    });
  } catch (error) {
    console.error("Error al cargar las ciudades:", error);
  }
}

async function loadProducts(cityId) {
  try {
    const response = await fetch(`${BASE_URL}/cities/${cityId}/products/`);
    if (!response.ok) {
      throw new Error("Error al cargar los productos");
    }
    const products = await response.json();
    const productsList = document.getElementById("productsList");
    productsList.innerHTML = "";
    products.forEach(product => {
      const productItem = document.createElement("li");
      productItem.textContent = `${product.name} - $${product.price}`;
      const deleteButton = document.createElement("button");
      deleteButton.textContent = "Eliminar";
      deleteButton.onclick = () => deleteProduct(cityId, product.id);
      productItem.appendChild(deleteButton);
      productsList.appendChild(productItem);
    });
  } catch (error) {
    console.error("Error al cargar los productos:", error);
  }
}

async function addProduct() {
  const cityId = document.getElementById("citySelect").value;
  const name = document.getElementById("productName").value;
  const price = parseFloat(document.getElementById("productPrice").value);

  try {
    const response = await fetch(`${BASE_URL}/cities/${cityId}/products/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, price })
    });

    if (response.ok) {
      alert("Producto agregado exitosamente");
      loadProducts(cityId);
    } else {
      throw new Error("Error al agregar el producto");
    }
  } catch (error) {
    console.error("Error al agregar el producto:", error);
  }
}

async function deleteProduct(cityId, productId) {
  try {
    const response = await fetch(`${BASE_URL}/cities/${cityId}/products/${productId}`, {
      method: "DELETE"
    });
    if (response.ok) {
      alert("Producto eliminado exitosamente");
      loadProducts(cityId);
    } else {
      throw new Error("Error al eliminar el producto");
    }
  } catch (error) {
    console.error("Error al eliminar el producto:", error);
  }
}

async function addCity() {
  const cityName = document.getElementById("newCityName").value;

  try {
    const response = await fetch(`${BASE_URL}/cities/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: cityName })
    });

    if (response.ok) {
      alert("Ciudad agregada exitosamente");
      loadCities();
    } else {
      throw new Error("Error al agregar la ciudad");
    }
  } catch (error) {
    console.error("Error al agregar la ciudad:", error);
  }
}

async function deleteCity(cityId) {
  try {
    const response = await fetch(`${BASE_URL}/cities/${cityId}`, {
      method: "DELETE"
    });
    if (response.ok) {
      alert("Ciudad eliminada exitosamente");
      loadCities();
    } else {
      throw new Error("Error al eliminar la ciudad");
    }
  } catch (error) {
    console.error("Error al eliminar la ciudad:", error);
  }
}

async function loadChatbotResponse() {
  const question = "Hola";
  try {
    const response = await fetch(`${BASE_URL}/chatbot/ask/?question=${encodeURIComponent(question)}`, {
      method: "POST",
      headers: { "Accept": "application/json" }
    });
    if (!response.ok) {
      throw new Error("Error al cargar la respuesta del chatbot");
    }
    const chatbotData = await response.json();
    const chatbotResponse = document.getElementById("chatbotResponse");
    chatbotResponse.textContent = chatbotData.answer;
  } catch (error) {
    console.error("Error al cargar la respuesta del chatbot:", error);
  }
}

async function sendMessage() {
  const question = document.getElementById("chatMessage").value;
  try {
    const response = await fetch(`${BASE_URL}/chatbot/ask/?question=${encodeURIComponent(question)}`, {
      method: "POST",
      headers: { "Accept": "application/json" }
    });
    if (response.ok) {
      const chatbotData = await response.json();
      document.getElementById("chatResponse").textContent = chatbotData.answer;
    } else {
      throw new Error("Error al obtener respuesta del chatbot");
    }
  } catch (error) {
    console.error("Error en sendMessage:", error);
  }
}

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
      loadFacebookAccounts();
    } else {
      throw new Error("Error al conectar la cuenta de Facebook");
    }
  } catch (error) {
    console.error("Error en addFacebookAccount:", error);
  }
}
