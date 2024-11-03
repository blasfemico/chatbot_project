
from fastapi import FastAPI
from app.database import Base, engine
from app.config import settings
from app.routes import chatbot, orders, websockets
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)

# Incluir las rutas con prefijos y etiquetas para organización
app.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(websockets.router, tags=["WebSocket"])


@app.get("/")
async def root():
    return {"message": "ping owo"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
