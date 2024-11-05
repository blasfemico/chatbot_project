from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request, Query
from sqlalchemy.orm import Session
from app.config import settings
from app.crud import CRUDFaq, CRUDMessage, CRUDFacebookAccount, CRUDCuentaProducto
from app.database import get_db
from pydantic import BaseModel
import requests
import PyPDF2
from openai import OpenAI
import json
import os
from app.models import Cuenta
import re

# Configuración de OpenAI y router
router = APIRouter()
VERIFY_TOKEN = "chatbot_project"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Prompt base para establecer el contexto de ChatGPT
assistant_prompt = (
    "Responde exclusivamente con la información proporcionada en la base de datos de manera directa, "
    "sin añadir aclaraciones, recordatorios o advertencias adicionales. Organiza la información de forma clara y profesional."
)

class FacebookAccount(BaseModel):
    api_key: str

def get_openai_response(question: str, cuenta: Cuenta, faq_crud: CRUDFaq, db: Session):
    # Obtener contexto de preguntas frecuentes de la base de datos
    faqs = faq_crud.get_all_faqs(db=db)
    faqs_text = "\n".join([f"Pregunta: {faq.question}\nRespuesta: {faq.answer}" for faq in faqs])

    cuenta_productos = CRUDCuentaProducto()
    productos = cuenta_productos.get_productos_by_cuenta(db=db, cuenta_id=cuenta.id)
    productos_text = "\n".join([f"{prod.producto.nombre}: {prod.precio}" for prod in productos])

    # Crear el prompt con contexto de productos y FAQs de la cuenta
    prompt = f"""
    Cuenta: {cuenta.nombre}
    Preguntas frecuentes:
    {faqs_text}
    
    Lista de productos y precios:
    {productos_text}
    
    Pregunta del usuario: "{question}"
    
    Responde de forma profesional basándote en la información de arriba.
    """

    # Obtener respuesta de ChatGPT
    response = client.chat.completions.create(model="gpt-4",
    messages=[
        {"role": "system", "content": assistant_prompt},
        {"role": "user", "content": prompt}
    ],
    max_tokens=150)
    return response.choices[0].message.content.strip()

@router.post("/chatbot/ask/")
async def ask_question(api_key: str = Query(..., description="API key de la cuenta"), question: str = Query(..., description="Pregunta del usuario"), db: Session = Depends(get_db)):
    # Identificar la cuenta asociada a la api_key
    cuenta = db.query(Cuenta).filter(Cuenta.api_key == api_key).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    # Obtener respuesta de OpenAI
    answer = get_openai_response(question, cuenta, CRUDFaq(), db)
    return {"respuesta": answer}

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

@router.post("/facebook/webhook/", response_model=None)
async def facebook_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    if 'hub.mode' in data and data['hub.mode'] == 'subscribe':
        return data.get('hub.challenge')

    # Procesar mensajes
    if 'entry' in data:
        for entry in data['entry']:
            for message_event in entry.get('messaging', []):
                if 'message' in message_event:
                    sender_id = message_event['sender']['id']
                    message_text = message_event['message'].get('text')
                    if message_text:
                        # Obtener la cuenta asociada al API key, en este caso puedes definir una cuenta por defecto
                        api_key = "TU_API_KEY_DEFECTO"  # Cambia esto por la lógica de obtención de la API key real
                        cuenta = db.query(Cuenta).filter(Cuenta.api_key == api_key).first()

                        if not cuenta:
                            raise HTTPException(status_code=404, detail="Cuenta no encontrada")

                        # Responder al usuario usando OpenAI o mensajes predefinidos
                        response_text = get_openai_response(message_text, cuenta, CRUDFaq(), db)
                        send_message(sender_id, response_text)

    return {"status": "ok"}

def send_message(recipient_id, text):
    url = f"{settings.FACEBOOK_GRAPH_API_URL}/me/messages"
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "access_token": settings.FACEBOOK_PAGE_ACCESS_TOKEN
    }
    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error al enviar el mensaje.")

def extract_questions_and_answers(content):
    prompt = (
        f"Extrae las preguntas y respuestas del siguiente texto y devuélvelo en formato JSON "
        f"estrictamente válido. Cada elemento debe estar en la forma {{'question': 'pregunta', 'answer': 'respuesta'}}.\n\n{content}"
    )
    response = client.chat.completions.create(model="gpt-4",
    messages=[{"role": "system", "content": assistant_prompt}, {"role": "user", "content": prompt}],
    max_tokens=500)
    response_text = response.choices[0].message.content.strip()
    return parse_response(response_text)

def parse_response(response_text):
    try:
        parsed_content = json.loads(response_text)
        if isinstance(parsed_content, list) and all(isinstance(item, dict) for item in parsed_content):
            return parsed_content
        else:
            raise ValueError("Formato JSON inválido: se esperaba una lista de diccionarios con 'question' y 'answer'.")
    except json.JSONDecodeError:
        cleaned_text = re.sub(r'^[^{\[]+', '', response_text)
        cleaned_text = re.sub(r'[^}\]]+$', '', cleaned_text)
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            raise ValueError("Error al procesar la respuesta de OpenAI: el formato de JSON es inválido.")

@router.post("/pdf/upload/")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = [page.extract_text() for page in PyPDF2.PdfReader(file.file).pages]
        questions_and_answers = extract_questions_and_answers("\n".join(content))

        if not isinstance(questions_and_answers, list) or not all(isinstance(item, dict) for item in questions_and_answers):
            raise ValueError("El contenido extraído no está en el formato esperado de lista de diccionarios.")

        faq_crud = CRUDFaq()
        faq_crud.create_pdf_with_faqs(db=db, content=questions_and_answers, pdf_name=file.filename)
        return {"message": "PDF cargado y procesado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el PDF: {str(e)}")

@router.get("/facebook/webhook/")
async def verify_webhook(request: Request):
    # Facebook envía 'hub.mode', 'hub.challenge' y 'hub.verify_token' en la solicitud de verificación
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    # Compara el token enviado por Facebook con tu VERIFY_TOKEN
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)  # Devuelve el challenge para verificar el webhook
    else:
        raise HTTPException(status_code=403, detail="Token de verificación inválido")

def collect_database_info(faq_crud, db):
    # Recopilar y estructurar respuestas de la base de datos para términos generales
    faqs = faq_crud.get_all_faqs(db=db)
    medications = [f"Pregunta: {faq.question}\nRespuesta: {faq.answer}" for faq in faqs if "medicamento" in faq.question.lower() or "precio" in faq.question.lower()]

    if medications:
        # Prepara el mensaje para el modelo de chat
        prompt = f"{assistant_prompt}\n\nOrganiza la siguiente información sobre medicamentos y precios:\n\n{''.join(medications)}"
        response = client.chat.completions.create(model="gpt-4",
        messages=[{"role": "system", "content": assistant_prompt}, {"role": "user", "content": prompt}],
        max_tokens=500)
        return response.choices[0].message.content.strip()
    return "No se encontró información específica sobre medicamentos o precios en la base de datos."
