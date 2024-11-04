from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.crud import CRUDFaq, CRUDMessage, CRUDFacebookAccount
from app.database import get_db
from pydantic import BaseModel
import requests
import PyPDF2
from openai import OpenAI
import json
from difflib import get_close_matches
import re
import os
from app.models import FAQ

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
router = APIRouter()

# Ajuste del prompt para evitar introducciones y recordatorios
assistant_prompt = (
    "Responde exclusivamente con la información proporcionada en la base de datos de manera directa, "
    "sin añadir aclaraciones, recordatorios o advertencias adicionales. Organiza la información de forma clara y profesional."
)

class FacebookAccount(BaseModel):
    api_key: str

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


def extract_questions_and_answers(content):
    prompt = (
        f"Extrae las preguntas y respuestas del siguiente texto y devuélvelo en formato JSON "
        f"estrictamente válido. Cada elemento debe estar en la forma {{'question': 'pregunta', 'answer': 'respuesta'}}.\n\n{content}"
    )
    response = client.chat.completions.create(model="gpt-4",
    messages=[
        {"role": "system", "content": assistant_prompt},
        {"role": "user", "content": prompt}
    ])
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


@router.post("/chatbot/ask/")
async def ask_question(question: str, db: Session = Depends(get_db)):
    faq_crud = CRUDFaq()

    # Detectar términos específicos como "info", "información", "lista de medicamentos" y recopilar información de la base de datos
    if question.lower() in ["info", "información", "lista de medicamentos"]:
        medications_info = collect_database_info(faq_crud, db)
        if medications_info:
            return {"answer": medications_info}

    # Buscar respuesta exacta en la base de datos
    exact_answer = faq_crud.get_response(db=db, question=question)
    if exact_answer != "Lo siento, no tengo una respuesta para esa pregunta.":
        return {"answer": exact_answer}

    # Buscar respuesta aproximada en la base de datos
    approximate_answer = get_approximate_response(db, question)
    if approximate_answer != "Lo siento, no tengo una respuesta para esa pregunta.":
        return {"answer": approximate_answer}

    # Si no se encuentra una respuesta en la base de datos, se consulta a OpenAI con contexto
    answer = get_openai_response(question, faq_crud, db)
    return {"answer": answer}


def collect_database_info(faq_crud, db):
    # Recopilar y estructurar respuestas de la base de datos para términos generales
    faqs = faq_crud.get_all_faqs(db=db)
    medications = [f"Pregunta: {faq.question}\nRespuesta: {faq.answer}" for faq in faqs if "medicamento" in faq.question.lower() or "precio" in faq.question.lower()]

    if medications:
        # Pide a OpenAI que organice las respuestas recolectadas sin introducción o recordatorios
        prompt = f"{assistant_prompt}\n\nOrganiza la siguiente información sobre medicamentos y precios:\n\n{''.join(medications)}"
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": assistant_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    return "No se encontró información específica sobre medicamentos o precios en la base de datos."


def get_approximate_response(db: Session, question: str):
    faqs = CRUDFaq().get_all_faqs(db)
    questions = [faq.question for faq in faqs]
    close_matches = get_close_matches(question, questions, n=1, cutoff=0.5)
    if close_matches:
        matched_question = close_matches[0]
        faq = db.query(FAQ).filter(FAQ.question == matched_question).first()
        return faq.answer if faq else "No se encontró una respuesta exacta para esa pregunta."
    return "No se encontró una respuesta para esa pregunta."


def get_openai_response(question: str, faq_crud: CRUDFaq, db: Session):
    context_faqs = faq_crud.get_all_faqs(db=db)
    context = "\n".join([f"Pregunta: {faq.question}\nRespuesta: {faq.answer}" for faq in context_faqs])
    prompt = f"{assistant_prompt}\n\nContexto:\n{context}\n\nPregunta: {question}\nRespuesta:"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": assistant_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()