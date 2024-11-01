# app/routes/chatbot.py
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
import requests
import PyPDF2
from app.crud import CRUDOrder, CRUDFaq  # Importación de CRUDFaq
from app.schemas import OrderCreate

router = APIRouter()

class FacebookAccount(BaseModel):
    api_key: str

FACEBOOK_GRAPH_API_URL = "https://graph.facebook.com/v12.0"

# Conectar una cuenta de Facebook y suscribirse a los mensajes
@router.post("/facebook/connect/")
async def connect_facebook(account: FacebookAccount):
    try:
        # Endpoint para suscribir la página a los mensajes
        url = f"{FACEBOOK_GRAPH_API_URL}/me/subscribed_apps"
        headers = {
            "Authorization": f"Bearer {account.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers)

        if response.status_code == 200:
            return {"status": "Conectado a Facebook Messenger"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al conectar: {str(e)}")


# Subir PDF y almacenar contenido para respuestas del chatbot
@router.post("/pdf/upload/")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        reader = PyPDF2.PdfReader(file.file)
        pdf_content = []

        for page in reader.pages:
            pdf_content.append(page.extract_text())

        # Procesar el texto para preguntas y respuestas
        questions_and_answers = parse_pdf_content(pdf_content)

        # Guardar el contenido procesado en la base de datos
        faq_crud = CRUDFaq()
        faq_crud.store_pdf_content(db=db, content=questions_and_answers)

        return {"message": "PDF cargado y procesado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el PDF: {str(e)}")


# Función auxiliar para procesar el contenido del PDF
def parse_pdf_content(content):
    questions_and_answers = []
    for line in content:
        # Divide cada pregunta y respuesta aquí
        # Ejemplo de formato esperado: "Pregunta: <texto> Respuesta: <texto>"
        if "Pregunta:" in line and "Respuesta:" in line:
            parts = line.split("Respuesta:")
            question = parts[0].replace("Pregunta:", "").strip()
            answer = parts[1].strip()
            questions_and_answers.append({"question": question, "answer": answer})
    return questions_and_answers


# Responder a preguntas de los usuarios basadas en el PDF
@router.post("/chatbot/ask/")
async def ask_question(question: str, db: Session = Depends(get_db)):
    faq_crud = CRUDFaq()
    answer = faq_crud.get_response(db=db, question=question)
    if answer:
        return {"answer": answer}
    else:
        return {"answer": "Lo siento, no tengo una respuesta para esa pregunta en el PDF."}
