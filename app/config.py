import os

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Puedes acceder a estas configuraciones desde cualquier parte del proyecto
# usando Config.DATABASE_URL, Config.SECRET_KEY, etc.
