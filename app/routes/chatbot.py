# app/routes/chatbot.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.crud import CRUDFaq
from app.database import get_db
import requests
import PyPDF2
from openai import OpenAI
from difflib import get_close_matches
from pydantic import BaseModel
from app.models import FAQ

router = APIRouter()

# Inicializar el cliente de OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Clase de datos para la clave API de Facebook
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

# Subir PDF y almacenar contenido para respuestas del chatbot
@router.post("/pdf/upload/")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        reader = PyPDF2.PdfReader(file.file)
        pdf_content = []
        
        # Leer y procesar cada página del PDF
        for page in reader.pages:
            pdf_content.append(page.extract_text())
        
        # Procesar el contenido en preguntas y respuestas
        questions_and_answers = parse_pdf_content(pdf_content)

        # Guardar preguntas y respuestas en la base de datos
        faq_crud = CRUDFaq()
        faq_crud.store_pdf_content(db=db, content=questions_and_answers)

        return {"message": "PDF cargado y procesado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el PDF: {str(e)}")

# Función para procesar el contenido del PDF
def parse_pdf_content(content):
    questions_and_answers = []
    for line in content:
        if "Pregunta:" in line and "Respuesta:" in line:
            parts = line.split("Respuesta:")
            question = parts[0].replace("Pregunta:", "").strip()
            answer = parts[1].strip()
            questions_and_answers.append({"question": question, "answer": answer})
    return questions_and_answers

# Preguntar al chatbot
@router.post("/chatbot/ask/")
async def ask_question(question: str, db: Session = Depends(get_db)):
    faq_crud = CRUDFaq()
    answer = faq_crud.get_response(db=db, question=question)

    if answer == "Lo siento, no tengo una respuesta para esa pregunta.":
        # Si no hay coincidencia exacta, busca una coincidencia aproximada
        answer = get_approximate_response(db, question)
        
        # Si no encuentra una coincidencia aproximada, utiliza OpenAI
        if answer == "Lo siento, no tengo una respuesta para esa pregunta.":
            answer = await get_openai_response(question, faq_crud, db)

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

# Función para generar una respuesta con OpenAI usando GPT-4 si no se encuentra en el PDF
async def get_openai_response(question: str, faq_crud: CRUDFaq, db: Session):
    # Extraer todas las preguntas y respuestas del PDF como contexto
    context_faqs = faq_crud.get_all_faqs(db=db)
    context = "\n".join([f"Pregunta: {faq.question}\nRespuesta: {faq.answer}" for faq in context_faqs])

    try:
        # Crear el prompt combinando el contexto y la pregunta
        prompt = f"{context}\n\nPregunta: {question}\nRespuesta:"
        
        response = await client.completions.create(
            model="gpt-3.5-turbo",  # Especifica el modelo GPT-4
            prompt=prompt,  # Usar prompt en lugar de messages
            max_tokens=150
        )
        return response['choices'][0]['text'].strip()
    except Exception as e:
        return f"Error al conectar con OpenAI: {str(e)}"