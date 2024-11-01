from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class FacebookAccount(BaseModel):
    api_key: str

@router.post("/connect/")
async def connect_facebook(account: FacebookAccount):
    # Lógica para conectar a Facebook usando la API Key
    try:
        # Simulación de conexión
        return {"status": "Conectado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al conectar: {str(e)}")
