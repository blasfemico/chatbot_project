// URL base del backend
const BASE_URL = "http://localhost:8000";

// Cargar ciudades al iniciar
document.addEventListener("DOMContentLoaded", loadCities);

async function loadCities() {
  const response = await fetch(`${BASE_URL}/cities/`);
  const cities = await response.json();
  const citySelect = document.getElementById("citySelect");
  citySelect.innerHTML = "";
  cities.forEach(city => {
    const option = document.createElement("option");
    option.value = city.id;
    option.text = city.name;
    citySelect.add(option);
  });
}

async function addProduct() {
  const cityId = document.getElementById("citySelect").value;
  const name = document.getElementById("productName").value;
  const price = parseFloat(document.getElementById("productPrice").value);

  const response = await fetch(`${BASE_URL}/cities/${cityId}/products/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, price })
  });

  if (response.ok) {
    alert("Producto agregado!");
    loadCities();
  } else {
    alert("Error al agregar producto.");
  }
}

async function sendMessage() {
  const message = document.getElementById("chatMessage").value;
  const response = await fetch(`${BASE_URL}/chatbot/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  const data = await response.json();
  document.getElementById("chatResponse").textContent = data.response;
}

async function uploadPDF() {
  const pdfFile = document.getElementById("pdfUpload").files[0];
  const formData = new FormData();
  formData.append("pdf", pdfFile);

  const response = await fetch(`${BASE_URL}/pdf/upload`, {
    method: "POST",
    body: formData
  });

  if (response.ok) {
    const data = await response.json();
    document.getElementById("pdfStatus").textContent = `PDF subido: ${data.pdf_name}`;
  } else {
    alert("Error al subir el PDF.");
  }
}

async function addFacebookAccount() {
  const name = document.getElementById("facebookName").value;
  const apiKey = document.getElementById("facebookApiKey").value;

  const response = await fetch(`${BASE_URL}/facebook/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account_name: name, api_key: apiKey })
  });

  if (response.ok) {
    alert("Cuenta de Facebook conectada!");
    loadFacebookAccounts();
  } else {
    alert("Error al conectar cuenta de Facebook.");
  }
}

async function loadFacebookAccounts() {
  const response = await fetch(`${BASE_URL}/facebook/accounts`);
  const accounts = await response.json();
  const list = document.getElementById("facebookAccountsList");
  list.innerHTML = "";
  accounts.forEach(account => {
    const listItem = document.createElement("li");
    listItem.textContent = account.account_name;
    list.appendChild(listItem);
  });
}
