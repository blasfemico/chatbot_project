# main.py
from fastapi import FastAPI
from app.database import Base, engine
from app.routes import chatbot, orders, websockets
from fastapi.middleware.cors import CORSMiddleware

# Inicializar la aplicación FastAPI
app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia "*" por los dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Incluir las rutas con prefijos y etiquetas para organización
app.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(websockets.router, tags=["WebSocket"])

# Ruta raíz para verificación
@app.get("/")
async def root():
    return {"message": "Bienvenido al Chatbot API"}

# Ejecuta solo si se llama directamente el archivo main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
