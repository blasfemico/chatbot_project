# app/cors.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import facebook, orders, pdf, chatbot

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia "*" por el dominio del frontend en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir las rutas
app.include_router(facebook.router, prefix="/facebook")
app.include_router(orders.router, prefix="/orders")
app.include_router(pdf.router, prefix="/pdf")
app.include_router(chatbot.router)
