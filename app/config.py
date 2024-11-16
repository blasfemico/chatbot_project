import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.FACEBOOK_GRAPH_API_URL = "https://graph.facebook.com/v12.0"
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.DEBUG_MODE = os.getenv("DEBUG_MODE", "True").lower() in ("true", "1")
        self.PROJECT_NAME = "Chatbot Project"

        # Cargar las API keys desde el archivo .env
        api_keys = os.getenv("API_KEYS")
        if api_keys:
            try:
                self.API_KEYS = json.loads(api_keys)
            except json.JSONDecodeError:
                raise ValueError("Formato inválido para API_KEYS en el archivo .env.")
        else:
            self.API_KEYS = {}

    def get_api_key(self, page_name: str) -> str:
        return self.API_KEYS.get(page_name, None)


# Instancia global
config = Config()
