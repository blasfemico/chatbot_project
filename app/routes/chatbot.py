from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.crud import CRUDFaq, CRUDMessage, CRUDFacebookAccount
from app.database import get_db
import requests
import PyPDF2
import os
import json
from openai import OpenAI
import re

client = OpenAI()

# Inicializar cliente de OpenAI
aclient = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from difflib import get_close_matches
from pydantic import BaseModel
from app.models import FAQ, Message

router = APIRouter()


class FacebookAccount(BaseModel):
    api_key: str

# Conectar una cuenta de Facebook y suscribirse a los mensajes
@router.post("/facebook/connect/")
async def connect_facebook(account: FacebookAccount):
    try:
        url = f"{settings.FACEBOOK_GRAPH_API_URL}/me/subscribed_apps"
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

# Función para extraer preguntas y respuestas usando OpenAI


def extract_questions_and_answers_with_ai(content):
    full_text = "\n".join(content)
    prompt = (
        f"Extrae las preguntas y respuestas del siguiente texto y devuélvelo en un formato JSON "
        f"estrictamente válido. Asegúrate de que el JSON contenga solo objetos con 'question' y 'answer' "
        f"y no incluya otros caracteres.\n\n{full_text}"
    )

    # Solicitud a OpenAI para procesar el texto
    response = client.chat.completions.create(model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "Eres un asistente que ayuda a extraer preguntas y respuestas de texto en un JSON válido."},
        {"role": "user", "content": prompt}
    ])

    # Accedemos al contenido de la respuesta
    response_text = response.choices[0].message.content.strip()

    try:
        questions_and_answers = json.loads(response_text)
        return questions_and_answers
    except json.JSONDecodeError:
        # Intentar corregir el JSON eliminando texto no válido y volviendo a cargarlo
        corrected_text = correct_json(response_text)
        try:
            return json.loads(corrected_text)
        except json.JSONDecodeError:
            raise ValueError("Error al procesar la respuesta de OpenAI: el formato de JSON es inválido.")

def correct_json(text):
    # Elimina caracteres extraños al inicio y al final del texto que puedan interferir con el formato JSON
    text = re.sub(r'^[^{\[]+', '', text)  # Elimina cualquier cosa antes del primer { o [
    text = re.sub(r'[^}\]]+$', '', text)  # Elimina cualquier cosa después del último } o ]
    return text
# Subir PDF y almacenar contenido para respuestas del chatbot

@router.post("/pdf/upload/")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        reader = PyPDF2.PdfReader(file.file)
        pdf_content = [page.extract_text() for page in reader.pages]

        
        questions_and_answers = extract_questions_and_answers_with_ai(pdf_content)

        
        faq_crud = CRUDFaq()
        faq_crud.create_pdf_with_faqs(db=db, pdf_name=file.filename, content=questions_and_answers)

        return {"message": "PDF cargado y procesado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el PDF: {str(e)}")

# Preguntar al chatbot, modificado para responder solo con el contenido del PDF
@router.post("/chatbot/ask/")
async def ask_question(question: str, db: Session = Depends(get_db)):
    faq_crud = CRUDFaq()
    answer = faq_crud.get_response(db=db, question=question)

    
    if answer == "Lo siento, no tengo una respuesta para esa pregunta.":
        answer = get_approximate_response(db, question)

    
    if answer == "Lo siento, no tengo una respuesta para esa pregunta.":
        return {"answer": "Lo siento, solo puedo responder preguntas relacionadas con el contenido proporcionado en este documento."}

    return {"answer": answer}

# Función para buscar coincidencias aproximadas en la base de datos
def get_approximate_response(db: Session, question: str):
    faq_crud = CRUDFaq()
    faqs = faq_crud.get_all_faqs(db)
    questions = [faq.question for faq in faqs]
    close_matches = get_close_matches(question, questions, n=1, cutoff=0.5)

    if close_matches:
        matched_question = close_matches[0]
        faq = db.query(FAQ).filter(FAQ.question == matched_question).first()
        return faq.answer if faq else "Lo siento, no tengo una respuesta exacta para esa pregunta."

    return "Lo siento, no tengo una respuesta para esa pregunta."

# Crear un mensaje nuevo
@router.post("/message/")
async def create_message(user_id: int, content: str, db: Session = Depends(get_db)):
    message_crud = CRUDMessage()
    new_message = message_crud.create_message(db=db, user_id=user_id, content=content)
    return {"message": "Mensaje guardado", "data": new_message}

# Obtener historial de mensajes
@router.get("/messages/")
async def get_messages(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    message_crud = CRUDMessage()
    messages = message_crud.get_messages(db=db, skip=skip, limit=limit)
    return {"data": messages}

# Agregar o actualizar cuenta de Facebook
@router.post("/facebook/account/")
async def add_or_update_facebook_account(account_name: str, api_key: str, db: Session = Depends(get_db)):
    facebook_crud = CRUDFacebookAccount()
    account = facebook_crud.get_facebook_account(db=db, account_name=account_name)
    if account:
        account = facebook_crud.update_facebook_account(db=db, account_name=account_name, api_key=api_key)
    else:
        account = facebook_crud.add_facebook_account(db=db, account_name=account_name, api_key=api_key)
    return {"message": "Cuenta de Facebook actualizada", "data": account}
