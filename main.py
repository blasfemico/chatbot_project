# app/main.py
from fastapi import FastAPI
from app.database import Base, engine
from app.routes import facebook, pdf, orders, websockets

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(facebook.router, prefix="/facebook", tags=["Facebook"])
app.include_router(pdf.router, prefix="/pdf", tags=["PDF"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(websockets.router)

@app.get("/")
async def root():
    return {"message": "Bienvenido al Chatbot API"}

# Ejecuta solo si se llama directamente el archivo main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
