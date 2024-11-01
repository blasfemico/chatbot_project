# app/config.py
import os
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Settings(BaseSettings):
    # Configuración de la base de datos
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Configuración de Facebook API
    FACEBOOK_GRAPH_API_URL: str = Field(default="https://graph.facebook.com/v12.0")
    FACEBOOK_PAGE_ACCESS_TOKEN: str = Field(..., env="FACEBOOK_PAGE_ACCESS_TOKEN")

    # Configuración de OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")

    # Configuración general
    PROJECT_NAME: str = Field(default="Chatbot Project")
    DEBUG_MODE: bool = Field(default=True, env="DEBUG_MODE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instancia de la configuración
settings = Settings()
