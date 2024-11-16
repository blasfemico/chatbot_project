from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routes import account_product, chatbot, orders, cities
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DEBUG_MODE:
        from sqlalchemy import inspect
        from app.database import Base, engine

        inspector = inspect(engine)
        if not inspector.get_table_names():
            Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chatbot.router, tags=["Chatbot"])
app.include_router(orders.router, tags=["Orders"])
app.include_router(account_product.router, tags=["Account Product"])
app.include_router(cities.router, tags=["Cities"])


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=settings.DEBUG_MODE)
