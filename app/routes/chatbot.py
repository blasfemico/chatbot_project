from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Cuenta,
    FAQ,
    CuentaProducto,
    Producto,
    ProductoCiudad,
    Ciudad
)
from app.crud import CRUDProduct, FAQCreate, CRUDFaq, CRUDCiudad, CRUDOrder
from app.schemas import Cuenta as CuentaSchema
from app.schemas import FAQSchema, FAQUpdate, APIKeyCreate
from app import schemas
from app.config import settings
from openai import OpenAI
import json
import os
import requests
from typing import List
from sentence_transformers import SentenceTransformer, util
import re
from datetime import datetime, date
from json import JSONDecodeError
import logging
from cachetools import TTLCache
import asyncio
import stanza
from threading import Lock
import time
from stanza import DownloadMethod
from collections import defaultdict

cache = TTLCache(maxsize=100, ttl=3600)
logging.basicConfig(level=logging.INFO)
router = APIRouter()
model = SentenceTransformer("all-MiniLM-L6-v2")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
crud_producto = CRUDProduct()
crud_faq = CRUDFaq(model)
VERIFY_TOKEN = "chatbot_project"
API_KEYS_FILE = "api_keys.json" 
processed_message_ids = set()
recent_messages = {}
recent_messages_lock = Lock()

class ChatbotService:
    initial_message_sent = defaultdict(lambda: False)
    order_timers = {} 
    user_contexts = {}
    product_embeddings = {} 
    model = SentenceTransformer("all-MiniLM-L6-v2")

    @staticmethod
    def extract_product_from_initial_message(initial_message: str) -> str:
        product_match = re.search(
            r"información sobre las (pastillas|producto|cápsulas) (\w+)", 
            initial_message, 
            re.IGNORECASE
        )
        if product_match:
            return product_match.group(2).capitalize()
        return "Acxion"
    
    @staticmethod
    def ensure_initial_message_sent(sender_id):
        """
        Asegura que el mensaje inicial sea enviado solo una vez por usuario.
        """
        if sender_id not in ChatbotService.initial_message_sent:
            ChatbotService.initial_message_sent[sender_id] = False

    @staticmethod
    def update_keywords_based_on_feedback(text: str):
        feedback_phrases = [
            "Muchas gracias", "No gracias", "ya no", "listo", "luego te hablo",
            "no necesito más", "ok", "gracias por info", "adios"
        ]
        for phrase in feedback_phrases:
            if phrase.lower() in text.lower():
                new_keyword = phrase.strip().lower()
                logging.info(f"Nueva palabra clave detectada para cierre: {new_keyword}")
                with open("keywords.txt", "a") as file:
                    file.write(f"{new_keyword}\n")

    @staticmethod
    def normalize_and_interpret_message(message: str) -> str:
        """
        Limpia, corrige y reorganiza el mensaje para interpretarlo correctamente.
        Combina varias técnicas de procesamiento de texto.
        """
        import re
        from unidecode import unidecode

        def clean_text(text: str) -> str:
            """
            Elimina caracteres no deseados, normaliza espacios y convierte a minúsculas.
            """
            text = unidecode(text) 
            text = re.sub(r"[^a-zA-Z0-9áéíóúüñ\s]", "", text)  
            text = re.sub(r"\s+", " ", text)  
            return text.strip().lower()

        def remove_redundancies(text: str) -> str:
            """
            Elimina redundancias o palabras repetidas innecesarias.
            """
            words = text.split()
            seen = set()
            deduplicated = []
            for word in words:
                if word not in seen:
                    deduplicated.append(word)
                    seen.add(word)
            return " ".join(deduplicated)

    
        logging.info(f"Mensaje original: {message}")
        message = clean_text(message)
        message = remove_redundancies(message)
        logging.info(f"Mensaje procesado: {message}")

        return message
    
    @staticmethod
    def handle_first_message(sender_id: str, db_response: str, primer_producto: str = "Acxion") -> str:
        print(f"2Mensaje inicial enviado a {sender_id}")
        print(f'2valor de ChatbotService.initial_message_sent: {ChatbotService.initial_message_sent}')
        """
        Genera y devuelve el mensaje inicial para el primer contacto de un cliente.
        Reemplaza los placeholders como "(revisar base de datos)" con valores reales de `db_response`.
        """
        prompt = f"""
        Eres un asistente de ventas que genera mensajes personalizados para los clientes.
        Asegúrate de reemplazar "(revisar base de datos)" con los valores reales de `db_response`.

        Producto estrella:
        ¡BAJA DE PESO FÁCIL Y RÁPIDO CON {primer_producto}!
        (resultados desde la primera o segunda semana)

        BENEFICIOS:
        • Baja alrededor de 6-10 kilos por mes ASEGURADO.
        • Acelera tu metabolismo y mejora la digestión.
        • Quema grasa y reduce tallas rápidamente.
        • Sin rebote / Sin efectos secundarios.

        Instrucciones: Tomar una pastilla al día durante el desayuno.
        Contenido: 30 tabletas por caja.

        Precio normal:
        1 caja: (revisar base de datos)
        PROMOCIONES:
        2 cajas: (revisar base de datos)
        3 cajas: (revisar base de datos)
        4 cajas: (revisar base de datos)
        5 cajas: (revisar base de datos)

        ¡Entrega a domicilio GRATIS y pagas al recibir!

        Si quieres hacer una orden, Mandame tu numero de telefono y te dare mas datos que necesito para hacer la orden
        recuerda mencionarme que productos quieres sino, pondre 1 caja de {primer_producto} para tu orden!

        db_response:
        {db_response}

        Genera un mensaje final que:
        - Reemplace "(revisar base de datos)" con los precios reales de `db_response`.
        - Mantenga el formato amigable y directo para los clientes.
        - No mencione que los datos provienen de una base de datos.
        - Devuelve estrictamente el mensaje sin encabezados ni notas adicionales.
        """
        print(f'primer_producto en handle_first_message: {primer_producto}')
        print(f'db_response en handle_first_message: {db_response}')

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
        
    @staticmethod
    def generate_humanlike_response(
        question: str,
        db_response: str,
        ciudades_disponibles: list,
        productos_por_ciudad: dict,
        chat_history: str = "", 
    ) -> str:
        logging.info(f"Recibido db_response en generate_humanlike_response: {db_response}")

        if not ciudades_disponibles or not isinstance(ciudades_disponibles, list):
            raise ValueError("El parámetro 'ciudades_disponibles' debe ser una lista no vacía.")
        if not productos_por_ciudad or not isinstance(productos_por_ciudad, dict):
            raise ValueError("El parámetro 'productos_por_ciudad' debe ser un diccionario no vacío.")
        ciudades_str = ", ".join([str(ciudad) for ciudad in ciudades_disponibles])
        productos_por_ciudad_str = "\n".join(
            [f"{ciudad.capitalize()}: {', '.join(map(str, productos))}" for ciudad, productos in productos_por_ciudad.items()]
        )
        ChatbotService.update_keywords_based_on_feedback(question)
     
        feedback_phrases = [
            "muchas gracias", "no gracias", "ya no", "listo", "luego te hablo",
            "no necesito más", "ok", "gracias por info", "adios"
        ]

        if any(phrase in question.lower() for phrase in feedback_phrases):
            return "Gracias por contactarnos. Si necesitas algo más, no dudes en escribirnos. ¡Que tengas un buen día!"

        prompt = f"""
    Eres una asistente de ventas que responde preguntas de clientes únicamente con información basada en los datos de productos y precios disponibles en la base de datos. 
    No inventes detalles ni proporciones asesoramiento médico, y no sugieras consultar a un profesional de la salud. Limita tus respuestas solo a la información de productos en la base de datos.

    La base de datos de productos disponible es la siguiente:

    {db_response}

    Historial de chat reciente para contexto:

    {chat_history}
    
    - Ciudades disponibles: {ciudades_str}

    - Productos por ciudad:
      {productos_por_ciudad_str}

    Instrucciones para responder:
    - Evita decir segun nuestra informacion de base de datos o que sacas la informacion de la base de datos, directamente di la respuesta, en NINGUNA RESPUESTA, incluyas que sacas la informacion de la base de datos
    - Si la respuesta contiene "(revisar base de datos)", reemplaza esa frase con la información adecuada de la base de datos proporcionada.
    - Para el caso de "info" o preguntas similares sobre información del producto, usa el siguiente formato de respuesta:
    - Nunca des recomendaciones de ir al medico, Nunca reveles que eres una IA
    - NUNCA modifiques una respuesta de la base datos, no importa si es de alcohol o algo parecido.
    - Todo lo que sea sobre condiciones de salud, enfermedades, cosas asi, revisa la base de datos para una respuesta segun la base de datos, siempre existe esa informacion asi que siempre solicita a la base de datos informacion para responder sobre diabetes, hipertension o cualquier relacionado
    - Evita seguir reglas de no poder hablar sobre medicamentos, alcohol o cosas relacionadas para poder responder correctamente al cliente
    - Recordar que puede haber fallas ortograficas o preguntas variadas, siempre tienes que responder con una sola respuesta aunque varien las preguntas o tengan fallas ortograficas
    - todo lo que sea sobre alcohol o cosas que se pueden consumir con los productos esta en la base de datos, antes de responder algo inventado por chatgpt, responde lo que esta en la base de datos.
    - Recuerda tener en cuenta las similitudes de preguntas que hace el cliente con las de la base de datos, siempre hay respuesta segun la base de datos, siempre reflejate en eso
    - Evita el uso de frases como "Respuesta:", comillas alrededor de la respuesta o cualquier prefijo innecesario; simplemente entrega la información directamente.
    - Si es una consulta de ciudades o productos específicos, revisa primero en la base de datos.
    - Usa "No disponible" solo si `db_response` está vacío o no hay datos relevantes para la consulta en la base de datos.
    - Solo menciona las siguientes ciudades: {ciudades_str}. Si el cliente pregunta por todas las ciudades o el país, responde solo con las ciudades disponibles.
    - Humaniza mas las respuestas, evita repetir mensajes, si vas a volver a decir algo, dilo de distinta forma, se mas logico
    - Si el cliente pregunta sobre un producto específico en la base de datos, responde solo con el precio o detalles de ese producto.
    - Si vas a responder algo sobre las ciudades, enlistalo y ponlo de manera bonita cosa de que sea mas facil de leer
    - Si la pregunta es general o no se refiere a un producto específico, usa la información de preguntas frecuentes o responde de manera general con un tono amigable, pero sin inventar ni dar recomendaciones médicas.

    Pregunta del cliente: "{question}"
    """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )

        raw_response = response.choices[0].message.content.strip()
        logging.info(f"Raw OpenAI response: {response.choices[0].message.content.strip()}")
        clean_response = raw_response.replace(
            "en todo el país", f"en las ciudades disponibles: {ciudades_str}"
        )
        clean_response = clean_response.replace(
            "todas las ciudades", f"las ciudades disponibles: {ciudades_str}"
        ).strip()

        if len(clean_response) < 4 or "No disponible" in clean_response:
            logging.info("Respuesta detectada como poco clara, solicitando aclaración al usuario.")
            return "Lo siento, no entendí completamente tu pregunta. ¿Podrías repetirla o hacerla de otra manera?"

        return clean_response
    

    @staticmethod
    async def search_faq_in_db(question: str, db: Session) -> str:
        faqs = crud_faq.get_all_faqs(db)

        if not faqs:
            return None

        faq_questions = [faq.question for faq in faqs]
        question_embedding = model.encode(question)
        embeddings = model.encode(faq_questions)

        if not embeddings.size:
            return None

        similarities = util.cos_sim(question_embedding, embeddings)[0]
        threshold = 0.42
        max_similarity_index = similarities.argmax().item()

        if similarities[max_similarity_index] >= threshold:
            return faqs[max_similarity_index].answer
        return None

    async def get_products_by_account(api_key: str, db: Session) -> dict:
        cuenta = db.query(Cuenta).filter(Cuenta.api_key == api_key).first()
        if not cuenta:
            raise HTTPException(
                status_code=404, detail="Cuenta no encontrada con esta API key"
            )

        productos = (
            db.query(CuentaProducto).filter(CuentaProducto.cuenta_id == cuenta.id).all()
        )

        if not productos:
            return {"respuesta": "No se encontraron productos para esta cuenta."}

        productos_info = [
            {"producto": producto.producto.nombre, "precio": producto.precio}
            for producto in productos
        ]

        return {"respuesta": productos_info}
    

    MODEL_DIR = "./stanza_resources"
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)

    stanza.download('es', model_dir=MODEL_DIR)  
    nlp = stanza.Pipeline(
        'es', 
        model_dir=MODEL_DIR, 
        processors='tokenize,ner', 
        download_method=DownloadMethod.REUSE_RESOURCES,
        quiet=True
    )

    @staticmethod
    def extract_address_from_text(message_text, sender_id, cuenta_id, db):
        message_text = re.sub(r'[^\w\sáéíóúüñ#,-]', '', message_text.lower())
        message_text = re.sub(r'([a-záéíóúüñ]+)(\d+)', r'\1 \2', message_text)
        direccion_patterns = [
            r'\b(?:calle|avenida|avda|av|paseo|ps|plaza|plz|carrer|cr|camino|cm|carretera|ctra)\s*[\wáéíóúüñ]*(?:\s+[\wáéíóúüñ]*)*\s+\d+',
            r'\b\d{1,5}\s*(?:calle|avenida|avda|av|paseo|ps|plaza|plz|carrer|cr|camino|cm|carretera|ctra)\s*[\wáéíóúüñ]*(?:\s+[\wáéíóúüñ]*)*\b',
            r'\b[\wáéíóúüñ]*(?:\s*[\wáéíóúüñ]*)*,?\s*\d{4,5}\b',
            r'\b(?:cll|av|cda|pt|cam|ct|pas|crt)\s*[\wáéíóúüñ]*(?:\s+[\wáéíóúüñ]*)*\s*\d+\b',
            r'\b[\wáéíóúüñ]*\s*#?\d+(?:\-\d+)?\b',
            r'\b\d+\s*[\wáéíóúüñ]*(?:\s+[\wáéíóúüñ]*)*\b',
            r'\b[\wáéíóúüñ]*(?:\s*[\wáéíóúüñ]*)*[\.,]?\s*\d+\b',
            r'\b[a-záéíóúüñ]+\d+\b'
        ]
        ciudades = [ciudad[0].lower() for ciudad in db.query(Ciudad.nombre).all()]
        productos = [producto[0].lower() for producto in db.query(Producto.nombre).all()]

        palabras_prohibidas = [
            "caja", "producto", "unidad", "botella", "tableta", "paquete", "kilogramo", "litro",
            "distrito", "barrio", "municipio", "región", "sector", "zona", "pueblo"
        ]
        palabras_prohibidas.extend(ciudades)
        palabras_prohibidas.extend(productos)
        telefono_detectado = ChatbotService.extract_phone_number(message_text)
        doc = ChatbotService.nlp(message_text)
        direccion = None
        for sentence in doc.sentences:
            for ent in sentence.ents:
                if ent.type == "LOC" and \
                not any(palabra in ent.text.lower() for palabra in palabras_prohibidas) and \
                (not telefono_detectado or telefono_detectado not in ent.text):
                    direccion = ent.text.strip()
                    print(f"Direccion en funcion extract_address_from_text1: {direccion}")
                    break
            if direccion:
                break
        if not direccion:
            for pattern in direccion_patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    posible_direccion = match.group(0).strip()
                    if not any(palabra in posible_direccion.lower() for palabra in palabras_prohibidas) and \
                    (not telefono_detectado or telefono_detectado not in posible_direccion):
                        direccion = posible_direccion
                        print(f"Direccion en funcion extract_address_from_text2: {direccion}")
                        break

        print(f"Direccion en funcion extract_address_from_text3: {direccion}")
        if direccion:
            if sender_id not in ChatbotService.user_contexts:
                ChatbotService.user_contexts[sender_id] = {}
            if cuenta_id not in ChatbotService.user_contexts[sender_id]:
                ChatbotService.user_contexts[sender_id][cuenta_id] = {}

            ChatbotService.user_contexts[sender_id][cuenta_id]["direccion"] = direccion
            return direccion

        return None

        
    def extract_city_from_text(input_text: str, db: Session) -> str:
        """
        Extrae el nombre de la ciudad del texto proporcionado.
        Utiliza el CRUD de Ciudad para hacer una búsqueda exacta o parcial en la base de datos.
        Se asegura de que no sea una acción como 'quiero ordenar' o frases similares.
        """
        input_text = input_text.lower().strip()

        action_phrases = [
            "hacer una orden", "quiero pedir", "voy a comprar", "quiero hacer un pedido",
            "ordenar", "comprar", "quiero ordenar", "voy a ordenar", "quiero hacer una compra",
            "me gustaría pedir", "necesito comprar", "quiero realizar una orden", "realizar un pedido",
            "quiero adquirir", "voy a hacer una compra", "quiero agendar un pedido", "necesito ordenar",
            "voy a hacer un pedido", "voy a realizar una compra", "quisiera comprar", "quiero hacer una compra",
            "voy a agendar un pedido", "quisiera realizar un pedido", "me gustaría hacer una orden",
            "necesito hacer un pedido", "voy a realizar un pedido", "voy a adquirir", "quiero agendar una compra",
            "quiero comprar algo", "quiero hacer mi pedido", "quiero un producto", "necesito agendar una compra",
            "quisiera hacer una compra", "necesito hacer una compra", "me interesa pedir",
            "voy a realizar una orden", "estoy interesado en pedir", "quisiera agendar un pedido",
            "me gustaría hacer un pedido", "quiero pedir algo", "quisiera ordenar", "voy a pedir",
            "quiero hacer una orden ahora", "estoy listo para pedir", "estoy listo para hacer una orden",
            "voy a realizar mi pedido", "necesito hacer un pedido ya", "quisiera agendar una orden",
            "voy a adquirir un producto", "quiero agendar un pedido ahora", "quisiera comprar algo",
            "quiero obtener el producto", "me interesa hacer un pedido", "necesito adquirir algo",
            "me gustaría ordenar ahora", "voy a comprar el producto", "quiero hacer mi orden", "order", "quiero", 
            "quiero agendar mi pedido", "quiero procesar una orden", "quiero adquirir el producto ahora", "quiero comprar", "voy a comprar"
        ]

        if any(phrase in input_text for phrase in action_phrases):
            return None

        ciudades = db.query(Ciudad.nombre).all()
        ciudades = [ciudad[0].lower() for ciudad in ciudades]

        for ciudad in ciudades:
            if ciudad in input_text:
                return ciudad.title()

        return None

    @staticmethod
    async def ask_question(
        question: str, sender_id: str, cuenta_id: int, db: Session
    ) -> dict:
        sanitized_question = ChatbotService.normalize_and_interpret_message(question)
        ChatbotService.update_keywords_based_on_feedback(question)
        context = ChatbotService.user_contexts.get(sender_id, {}).get(cuenta_id, {})
        logging.info(f"Contexto actualizado para sender_id {sender_id}: {context}")
        ciudades_disponibles = CRUDCiudad.get_all_cities(db)
        ciudades_nombres = [ciudad.nombre.lower() for ciudad in ciudades_disponibles]
        productos_por_ciudad = {}
        for ciudad in ciudades_disponibles:
            productos = (
                db.query(Producto)
                .join(ProductoCiudad)
                .filter(ProductoCiudad.ciudad_id == ciudad.id)
                .all()
            )
            productos_nombres = [producto.nombre for producto in productos]
            if productos_nombres:
                productos_por_ciudad[ciudad.nombre.lower()] = productos_nombres

        productos_por_ciudad_str = "\n".join(
            [f"{ciudad.capitalize()}: {', '.join(productos)}" for ciudad, productos in productos_por_ciudad.items()]
        )
        intent_prompt = f"""
        Eres un asistente de ventas que ayuda a interpretar preguntas sobre disponibilidad de productos en ciudades específicas.

        Disponemos de productos en las siguientes ciudades y productos asociados:
        {productos_por_ciudad_str}.

        La pregunta del cliente es: "{sanitized_question}"

        Responde estrictamente en JSON con:
        - "intent": "productos_ciudad" si la pregunta trata de disponibilidad de productos en una ciudad específica.
        - "intent": "listar_ciudades" si la pregunta solicita solo la lista de ciudades, abarca cualquier pregunta relacionada con ciudades.
        - "intent": "listar_productos" si la pregunta solicita la lista de todos los productos.
        - "intent": "otro" para preguntas no relacionadas con productos o ciudades.
        - "ciudad": el nombre de la ciudad en la pregunta, si aplica. No pongas "ciudad": null.
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": intent_prompt}],
                max_tokens=200,
            )
            raw_response = response.choices[0].message.content.strip()
            intent_data = json.loads(raw_response)
        except (JSONDecodeError, Exception) as e:
            logging.error(f"Error al identificar intención: {str(e)}")
            intent_data = {"intent": "otro"}
        if intent_data.get("intent") == "listar_productos":
            context["intencion_detectada"] = "listar_productos"
            productos = crud_producto.get_productos_by_cuenta(db, cuenta_id)
            db_response = "\n".join([f"{prod['producto']}: Precio {prod['precio']} pesos" for prod in productos])
            context["intencion_detectada"] = None
            return {"respuesta": db_response}

        elif intent_data.get("intent") == "productos_ciudad" and intent_data.get("ciudad"):
            ciudad_nombre = intent_data["ciudad"].lower()
            if ciudad_nombre in productos_por_ciudad:
                productos_nombres = productos_por_ciudad[ciudad_nombre]
                db_response = (
                    f"Los productos disponibles en {ciudad_nombre.capitalize()} son: {', '.join(productos_nombres)}."
                    if productos_nombres
                    else f"No hay productos disponibles en {ciudad_nombre.capitalize()}."
                )
            else:
                db_response = f"Lo siento, pero no tenemos productos disponibles en la ciudad {ciudad_nombre.capitalize()}."

        elif intent_data.get("intent") == "listar_ciudades":
            db_response = f"Disponemos de productos en las siguientes ciudades:\n{', '.join(productos_por_ciudad.keys())}."

        else:
            faq_answer = await ChatbotService.search_faq_in_db(sanitized_question, db)
            productos = crud_producto.get_productos_by_cuenta(db, cuenta_id)
            db_response = "\n".join(
                [f"{prod['producto']}: Precio {prod['precio']} pesos" for prod in productos]
            )
            if faq_answer:
                db_response = f"{faq_answer}\n\n{db_response}"

        if sender_id not in ChatbotService.initial_message_sent or not ChatbotService.initial_message_sent[sender_id]:
            ChatbotService.initial_message_sent[sender_id] = True
            primer_producto = ChatbotService.extract_product_from_initial_message(question)
            response = ChatbotService.generate_humanlike_response(
                question=sanitized_question,
                db_response=db_response,
                productos_por_ciudad=productos_por_ciudad,
                ciudades_disponibles=ciudades_disponibles,
                primer_producto=primer_producto,
            )
            return {"respuesta": response}
        try:
            respuesta = ChatbotService.generate_humanlike_response(
                question=sanitized_question, 
                db_response=db_response, 
                ciudades_disponibles=ciudades_disponibles,
                productos_por_ciudad=productos_por_ciudad,
              )

        except Exception as e:
            logging.error(f"Error al generar respuesta humanlike: {str(e)}")
            respuesta = "Hubo un problema al procesar tu solicitud. Por favor, intenta de nuevo más tarde."

        if not respuesta or respuesta == "Perdón, no entendí tu pregunta. ¿Podrías reformularla?":
            return {"respuesta": "Lo siento, no entendí tu pregunta. ¿Podrías repetirla o hacerla de otra manera?"}

        return {"respuesta": respuesta}



    @staticmethod
    def parse_product_input(input_text: str) -> List[dict]:
        """
        Convierte cadenas como '5 cajas de Acxion y 3 cajas de Redotex' en listas de diccionarios.
        """
        productos = []
        try:
            items = re.split(r"\s*y\s*", input_text.lower()) 
            for item in items:
                match = re.match(r"(\d+)\s*cajas?\s+de\s+(.+)", item.strip())
                if match:
                    cantidad = int(match.group(1))
                    producto = match.group(2).strip()
                    productos.append({"producto": producto, "cantidad": cantidad})
        except Exception as e:
            raise ValueError(f"Error al procesar la entrada de productos: {e}")
        return productos


    @staticmethod
    def extract_phone_number(text: str):
        phone_match = re.search(r"\+?\d{10,15}", text)
        phone_number = phone_match.group(0) if phone_match else None
        logging.info(f"Número de teléfono detectado: {phone_number}")
        return phone_number
    
    @staticmethod
    def extract_product_and_quantity(text: str, db: Session) -> list:
        productos_detectados = []
        productos = db.query(Producto).all()

        if not productos:
            logging.warning("No hay productos disponibles en la base de datos. Continuando sin detección de productos.")
            return productos_detectados 

        nombres_productos = [producto.nombre.lower() for producto in productos]
        cantidad_matches = re.findall(r"(\d+)\s*cajas?\s*de\s*([\w\s]+)", text, re.IGNORECASE)
        if cantidad_matches:
            for match in cantidad_matches:
                if len(match) >= 2:
                    cantidad, producto = int(match[0]), match[1].strip().lower()
                    producto_detectado = next((p for p in nombres_productos if producto in p), None)
                    if producto_detectado:
                        productos_detectados.append({"producto": producto_detectado, "cantidad": cantidad})
        if not productos_detectados:
            text_embedding = ChatbotService.model.encode(text, convert_to_tensor=True)
            productos_embeddings = ChatbotService.model.encode(nombres_productos, convert_to_tensor=True)
            similarities = util.cos_sim(text_embedding, productos_embeddings)[0]

            max_similarity_index = similarities.argmax().item()
            max_similarity_value = similarities[max_similarity_index]
            threshold = 0.5

            if max_similarity_value >= threshold:
                producto_detectado = nombres_productos[max_similarity_index]
                cantidad_match = re.findall(r"\b(\d+)\b", text)
                cantidad = int(cantidad_match[0]) if cantidad_match else 1  
                productos_detectados.append({"producto": producto_detectado, "cantidad": cantidad})

        if not productos_detectados:
            logging.info("No se detectaron productos en el mensaje del usuario. Continuando con flujo estándar.")

        logging.info(f"Productos detectados: {productos_detectados}")
        return productos_detectados

    @staticmethod
    def load_product_embeddings(db: Session):
        """
        Carga los embeddings de productos desde la base de datos.
        """
        productos = db.query(Producto).all()  
        nombres_productos = [producto.nombre for producto in productos]

        if not nombres_productos:
            logging.warning("No se encontraron productos en la base de datos para cargar embeddings.")
            return

        embeddings = ChatbotService.model.encode(nombres_productos, convert_to_tensor=True)
        ChatbotService.product_embeddings = dict(zip(nombres_productos, embeddings))
        logging.info(f"Embeddings de productos cargados: {list(ChatbotService.product_embeddings.keys())}")

    @staticmethod
    def get_product_list(db: Session) -> list:
        if not ChatbotService.product_list_cache:
            productos = db.query(Producto).all()
            ChatbotService.product_list_cache = [{"id": prod.id, "nombre": prod.nombre} for prod in productos]
        return ChatbotService.product_list_cache

    @staticmethod
    def clear_product_cache():
        ChatbotService.product_list_cache = None 

    @staticmethod
    def cache_response(question, response):
        cache.set(question, json.dumps(response), ex=3600) 

    @staticmethod
    def get_cached_response(question):
        cached_response = cache.get(question)
        if cached_response:
            return json.loads(cached_response)
        return None

    @staticmethod
    def get_response(question):
        cached_response = ChatbotService.get_cached_response(question)
        if cached_response:
            return cached_response
        else:
            response = client.chat.completions.create(...)  
            ChatbotService.cache_response(question, response)
            return response

def get_delivery_day_response():
    """Determina el día de entrega basado en el día de la semana."""
    today = date.today().weekday()

    if today in [5, 6]:
        delivery_day = "lunes"
    else:
        delivery_day = "mañana"

    return f"Su pedido se entregará el {delivery_day}."


class FAQService:
    @router.post("/faq/bulk_add/")
    async def bulk_add_faq(faqs: List[FAQCreate], db: Session = Depends(get_db)):
        for faq in faqs:
            db_faq = FAQ(question=faq.question, answer=faq.answer)
            db.add(db_faq)
        db.commit()
        return {"message": "Preguntas y respuestas añadidas correctamente"}

    @router.put("/faq/update/{faq_id}")
    async def update_faq(
        faq_id: int, question: str, answer: str, db: Session = Depends(get_db)
    ):
        faq_data = FAQUpdate(question=question, answer=answer)
        updated_faq = crud_faq.update_faq(db, faq_id, faq_data)

        if updated_faq:
            return {
                "message": f"Pregunta frecuente con ID {faq_id} actualizada correctamente",
                "faq": updated_faq,
            }
        else:
            return {"message": f"No existe una pregunta frecuente con ID {faq_id}"}

    @router.delete("/faq/delete/{faq_id}")
    async def delete_faq(faq_id: int, db: Session = Depends(get_db)):
        crud_faq.delete_faq(db, faq_id)
        return {"message": "FAQ eliminada correctamente"}

    @router.get("/faq/all", response_model=List[FAQSchema])
    async def get_all_faqs(db: Session = Depends(get_db)):
        """
        Endpoint para obtener todas las preguntas y respuestas de la base de datos.
        """
        faqs = crud_faq.get_all_faqs(db)
        return faqs
    
    @router.delete("/faq/delete_all/")
    async def delete_all_faqs(db: Session = Depends(get_db)):
        """
        Elimina todas las preguntas frecuentes de la base de datos.
        """
        faqs = crud_faq.get_all_faqs(db)
        for faq in faqs:
            db.delete(faq)
        db.commit()
        return {"message": "Todas las FAQs han sido eliminadas correctamente."}


class FacebookService:
    @staticmethod
    async def connect_facebook(account: CuentaSchema, db: Session) -> dict:
        url = f"{settings.FACEBOOK_GRAPH_API_URL}/me/subscribed_apps"
        headers = {
            "Authorization": f"Bearer {settings.FACEBOOK_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return {"status": "Conectado a Facebook Messenger"}
        else:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )


class FacebookService:
    API_KEYS_FILE = "api_keys.json"
    @staticmethod
    def get_api_key_by_page_id(page_id: str) -> str:
        """
        Busca la API Key correspondiente a un page_id específico en el archivo api_keys.json.
        """
        api_keys = FacebookService.load_api_keys()
        api_key = api_keys.get(page_id)

        if not api_key:
            logging.warning(f"No se encontró una API Key para la página con ID {page_id}")
            return None

        return api_key

    @staticmethod
    async def facebook_webhook(request: Request, db: Session):
        """
        Maneja los eventos del webhook de Facebook Messenger.
        """
        order_intent_phrases = [
            "hacer una orden", "quiero pedir", "voy a comprar", "quiero hacer un pedido",
            "ordenar", "comprar", "quiero ordenar", "voy a ordenar", "quiero hacer una compra",
            "me gustaría pedir", "necesito comprar", "quiero realizar una orden", "realizar un pedido",
            "quiero adquirir", "voy a hacer una compra", "quiero agendar un pedido", "necesito ordenar",
            "voy a hacer un pedido", "voy a realizar una compra", "quisiera comprar", "quiero hacer una compra",
            "voy a agendar un pedido", "quisiera realizar un pedido", "me gustaría hacer una orden",
            "necesito hacer un pedido", "voy a realizar un pedido", "voy a adquirir", "quiero agendar una compra",
            "quiero comprar algo", "quiero hacer mi pedido", "quiero un producto", "necesito agendar una compra",
            "quisiera hacer una compra", "necesito hacer una compra", "me interesa pedir",
            "voy a realizar una orden", "estoy interesado en pedir", "quisiera agendar un pedido",
            "me gustaría hacer un pedido", "quiero pedir", "quisiera ordenar", "voy a pedir",
            "quiero hacer una orden ahora", "estoy listo para pedir", "estoy listo para hacer una orden",
            "voy a realizar mi pedido", "necesito hacer un pedido ya", "quisiera agendar una orden",
            "voy a adquirir un producto", "quiero agendar un pedido ahora", "quisiera comprar algo",
            "quiero obtener el producto", "me interesa hacer un pedido", "necesito adquirir algo",  
            "me gustaría ordenar ahora", "voy a comprar el producto", "quiero hacer mi orden", "order",  
            "quiero agendar mi pedido", "quiero procesar una orden", "quiero adquirir el producto ahora",  "voy a comprar", 
            "ocupo", "quiero", 
        ]

        try:
            data = await request.json()
            logging.info(f"Payload recibido: {data}")
            if "entry" not in data or not data["entry"]:
                logging.error("Payload inválido: Falta la clave 'entry' o está vacía")
                raise HTTPException(status_code=400, detail="Entrada inválida en el payload")
        except Exception as e:
            logging.error(f"Error procesando JSON del webhook: {str(e)}")
            raise HTTPException(status_code=400, detail="Error en el payload recibido")

        for entry in data["entry"]:
            page_id = entry.get("id")
            cuenta = db.query(Cuenta).filter(Cuenta.page_id == page_id).first()

            if not cuenta:
                logging.warning(f"No se encontró ninguna cuenta para page_id {page_id}")
                continue

            cuenta_id = cuenta.id
            api_key = FacebookService.get_api_key_by_page_id(page_id)

            if not api_key:
                logging.error(f"No se encontró una API Key para la página con ID {page_id}")
                continue

            for event in entry.get("messaging", []):
                message_id = event.get("message", {}).get("mid")
                if message_id in processed_message_ids:
                    logging.info(f"Mensaje duplicado detectado: {message_id}. Ignorando.")
                    continue

                processed_message_ids.add(message_id)

                if "message" in event and not event.get("message", {}).get("is_echo"):
                    sender_id = event["sender"]["id"]
                    message_text = event["message"].get("text", "").strip()
                    ad_id = event.get("message", {}).get("referral", {}).get("ad_id", None)
                    is_audio = "audio" in event["message"].get("attachments", [{}])[0].get("type", "")

                    normalized_message = ChatbotService.normalize_and_interpret_message(message_text)
                    logging.info(f"Mensaje normalizado: {normalized_message}")

                    if sender_id not in ChatbotService.initial_message_sent:
                        ChatbotService.initial_message_sent[sender_id] = False
                        print(f"Inicializando sender_id {sender_id} como False")
                        print(f"Valor después de inicializar: {ChatbotService.initial_message_sent[sender_id]}")

                    print(f"Estado actual de ChatbotService.initial_message_sent antes de verificar: {ChatbotService.initial_message_sent}")
                    print(f"Verificando valor específico para sender_id {sender_id}: {ChatbotService.initial_message_sent[sender_id]}")

                    mensaje_inicial_enviado = ChatbotService.initial_message_sent[sender_id]
                    if not mensaje_inicial_enviado:
                        print(f"Enviando mensaje inicial a {sender_id} porque mensaje_inicial_enviado es {mensaje_inicial_enviado}")
                        db_response = "\n".join(
                            [f"{prod['producto']}: Precio {prod['precio']} pesos" for prod in crud_producto.get_productos_by_cuenta(db, cuenta_id)]
                            )   
                        primer_producto = ChatbotService.extract_product_from_initial_message(message_text)
                        response = ChatbotService.handle_first_message(sender_id, db_response, primer_producto)
                        await FacebookService.send_text_message(sender_id, response, api_key)
                        ChatbotService.initial_message_sent[sender_id] = True
                        return


                    if is_audio:
                        response_text = (
                            "Lo siento, no puedo escuchar audios en este momento. Por favor, escribe tu mensaje para que pueda ayudarte."
                        )
                        logging.info("Audio detectado. Enviando respuesta informativa al usuario.")
                        await FacebookService.send_text_message(sender_id, response_text, api_key)
                        continue

                    if cuenta_id not in ChatbotService.user_contexts:
                        ChatbotService.user_contexts[cuenta_id] = {}

                    user_context = ChatbotService.user_contexts[cuenta_id].get(sender_id, {})
                    user_profile = FacebookService.get_user_profile(sender_id, api_key)

                    if not user_context:
                        user_profile = FacebookService.get_user_profile(sender_id, api_key)
                        if user_profile:
                            ChatbotService.user_contexts[cuenta_id][sender_id] = {
                                "nombre": user_profile.get("first_name", "Cliente") if user_profile else "Cliente",
                                "apellido": user_profile.get("last_name", "Apellido") if user_profile else "Apellido",
                                "productos": [],
                                "telefono": None,
                                "ad_id": ad_id if ad_id else None,
                                "intencion_detectada": None,
                                "ciudad": None,
                                "direccion": None,
                                "fase_actual": "iniciar_orden" if any(phrase in message_text for phrase in order_intent_phrases) else "espera",
                                "fecha_inicio_orden": datetime.now(),
                                "orden_flujo_aislado": False,
                                "mensaje_predeterminado_enviado": False,
                                "pregunta": message_text,
                                "orden_creada": False,
                                "mensaje_faltante_enviado": False,
                                "mensaje_creacion_enviado": False,
                                "mensaje_creacion_enviado2": False,
                                "saltear_mensaje_faltante": False
                            }

                    context = ChatbotService.user_contexts[cuenta_id][sender_id]
                    telefono = ChatbotService.extract_phone_number(message_text)
            
                    if telefono:
                        context["telefono"] = telefono if telefono else context.get("telefono")
                        context["orden_flujo_aislado"] = True
                        ChatbotService.user_contexts[cuenta_id][sender_id] = context
                        logging.info(f"Número de teléfono o dirección detectados. Activando flujo aislado. Teléfono: {telefono}")
                    
                    productos_detectados = ChatbotService.extract_product_and_quantity(message_text, db)
                    if productos_detectados:
                        context["productos"] = productos_detectados
                        logging.info(f"Productos detectados: {productos_detectados}")   
                        context = ChatbotService.user_contexts[cuenta_id][sender_id]
                    else:
                        logging.info("No se detectaron productos en el mensaje.")
                    
                    if any(phrase in message_text for phrase in order_intent_phrases):
                        context["orden_flujo_aislado"] = True
                        context["mensaje_creacion_enviado"] = False 

                    print(f'CONTEXTO antes de orden flujo aislado: {context}')
                    if context.get("orden_flujo_aislado"): 
                        context["mensaje_creacion_enviado"] = False 
                        if not context.get("mensaje_predeterminado_enviado"):
                            response_text = (
                                "Para agendar tu pedido solo necesito los siguientes datos:\n"
                                "• Tu número de teléfono\n"
                                "• Dirección con número de casa\n"
                                "• Ciudad en la que vives\n"
                                "• Número de cajas que necesitas"
                            )
                            logging.info(f"Flujo aislado activado. Respuesta: {response_text}")
                            await FacebookService.send_text_message(sender_id, response_text, api_key)
                            context["mensaje_predeterminado_enviado"] = True
                            ChatbotService.user_contexts[cuenta_id][sender_id] = context

                        ciudad = ChatbotService.extract_city_from_text(message_text, db)
                        direccion = ChatbotService.extract_address_from_text(message_text, cuenta_id, sender_id, db)
                        telefono = ChatbotService.extract_phone_number(message_text)
                        productos_detectados = ChatbotService.extract_product_and_quantity(message_text, db)
                        pregunta_similar =  await ChatbotService.search_faq_in_db(message_text, db)

                        if pregunta_similar:
                            logging.info(f"Pregunta similar detectada: {pregunta_similar}. Saliendo del flujo aislado.")
                            context["orden_flujo_aislado"] = False
                            context["orden_creada"] = True
                            ChatbotService.user_contexts[cuenta_id][sender_id] = context
                            response_data = await ChatbotService.ask_question(
                                question=message_text,
                                sender_id=sender_id,
                                cuenta_id=cuenta_id,
                                db=db,
                            )
                            response_text = response_data.get("respuesta", "Lo siento, no entendí tu mensaje.")
                            await FacebookService.send_text_message(sender_id, response_text, api_key)
                            return  
                        
                        if productos_detectados:
                            context["productos"] = productos_detectados
                            logging.info(f"Productos detectados: {productos_detectados}")
                        else:
                            logging.info("No se detectaron productos en el mensaje.")

                        if not productos_detectados:
                            primer_producto = ChatbotService.extract_product_from_initial_message(message_text)
                            productos_detectados = [{"producto": primer_producto, "cantidad": 1}]
                            logging.info(f"No se detectaron productos, se agregó el producto predeterminado: {productos_detectados}")
                            context["productos"] = productos_detectados
                            ChatbotService.user_contexts[cuenta_id][sender_id] = context

                        datos_extraidos = {
                            "ciudad": ciudad,
                            "direccion": direccion,
                            "telefono": telefono
                        }

                        for key, value in datos_extraidos.items():
                            if value and context.get(key) != value:
                                context[key] = value
                                logging.info(f"Actualizado {key}: {value}")
                        
                        ChatbotService.user_contexts[cuenta_id][sender_id] = context

                        await asyncio.sleep(180)
                        datos_faltantes = []
                        if not context.get("telefono"):
                            datos_faltantes.append("número de teléfono")
                        if not context.get("direccion"):
                            datos_faltantes.append("dirección con número de casa")
                        if not context.get("ciudad"):
                            datos_faltantes.append("ciudad")
                        if not context.get("productos"):
                            datos_faltantes.append("número de cajas que necesitas")


                        if datos_faltantes and not context.get("mensaje_faltante_enviado") and context["orden_flujo_aislado"]:
                            reminder_text = (
                                "Hola, aún no hemos recibido toda la información. Por favor, proporciona los siguientes datos para continuar:\n"
                                f"- {', '.join(datos_faltantes)}"
                            )
                            await FacebookService.send_text_message(sender_id, reminder_text, api_key)
                            context["mensaje_faltante_enviado"] = True
                            ChatbotService.user_contexts[cuenta_id][sender_id] = context

                        elif context.get("telefono") and context.get("direccion") and context.get("ciudad") and context.get("productos") and context["orden_flujo_aislado"]:
                            print("if con todos los datos")
                            if not context.get("orden_creada"):
                                print("datos del contexto: ", context)
                                try:
                                    nombre = context.get("nombre", "Cliente")
                                    apellido = context.get("apellido", "Apellido")
                                    productos = context["productos"]
                                    ciudad = context.get("ciudad", "N/A")
                                    direccion = context.get("direccion", "N/A")
                                    cantidad_cajas = sum([p["cantidad"] for p in productos])
                                    telefono = context.get("telefono")
                                    email = context.get("email", "N/A")

                                    productos_info = crud_producto.get_productos_by_cuenta(db, cuenta_id)

                                    for producto in productos:
                                        producto_nombre = f"{producto['producto']} ({producto['cantidad']})".lower()
                                        producto["precio"] = next(
                                            (prod['precio'] for prod in productos_info if prod['producto'].lower() == producto_nombre),
                                            0  
                                        )
                                       

                                    cantidad_cajas = sum([p["cantidad"] for p in productos])
                                    ChatbotService.user_contexts[cuenta_id][sender_id] = context

                                    print(f'productos: {productos}')
                                    print(f'cantidad_cajas: {cantidad_cajas}')
                                    print(f'producto nomnre: {producto_nombre}')
                                    
                                
                                    order_data = schemas.OrderCreate(
                                        phone=telefono,
                                        email=email,
                                        address=direccion,
                                        producto=productos,
                                        cantidad_cajas=cantidad_cajas,
                                        ciudad=ciudad,
                                        ad_id=context.get("ad_id", "N/A"),
                                    )

                                    crud_order = CRUDOrder()
                                    nueva_orden = crud_order.create_order(db=db, order=order_data, nombre=nombre, apellido=apellido)

                                    respuesta = (
                                        f"✅ Su pedido ya quedó registrado:\n"
                                        f"📦 Sus productos llegarán pronto!\n"
                                        f"📞 Teléfono: {telefono}\n"
                                        f"📍 Ciudad: {ciudad}\n"
                                        "El repartidor se comunicará contigo entre 8 AM y 9 PM para confirmar la entrega. ¡Gracias por tu compra! 😊"
                                    )
                                    await FacebookService.send_text_message(sender_id, respuesta, api_key)
                                    context["orden_creada"] = True

                                    ChatbotService.user_contexts[cuenta_id][sender_id] = context
                                    print(f'orden_creada: {context["orden_creada"]}')
                                    logging.info(f"Orden creada exitosamente: {nueva_orden}")

                                except Exception as e:
                                    logging.error(f"Error al crear la orden: espere porfavor")


                        await asyncio.sleep(180)

                        if not context.get("telefono") and context["orden_flujo_aislado"]:

                            cancel_text = (
                                "No podemos procesar tu pedido porque falta el número de teléfono. "
                                "Por favor, proporciona toda la información necesaria para continuar."
                            )
                            await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                            logging.info("Pedido rechazado por falta de número de teléfono.")
                            context["orden_creada"] = True  

                        if context.get("telefono") and not context.get("productos") and context["orden_flujo_aislado"]:

                            cancel_text = (
                                "Lamentablemente, no hemos recibido información suficiente sobre los productos. "
                                "El pedido no se ha completado."
                            )
                            await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                            context["orden_creada"] = True
                            ChatbotService.user_contexts[cuenta_id][sender_id] = context

                        elif context.get("telefono") and context.get("direccion") and context.get("ciudad") and context.get("productos") and context["orden_flujo_aislado"]:
                            print("if con todos los datos")
                            if not context.get("orden_creada"):
                                print("datos del contexto: ", context)
                                try:
                                    nombre = context.get("nombre", "Cliente")
                                    apellido = context.get("apellido", "Apellido")
                                    productos = context["productos"]
                                    ciudad = context.get("ciudad", "N/A")
                                    direccion = context.get("direccion", "N/A")
                                    cantidad_cajas = sum([p["cantidad"] for p in productos])
                                    telefono = context.get("telefono")
                                    email = context.get("email", "N/A")

                                    productos_info = crud_producto.get_productos_by_cuenta(db, cuenta_id)

                                    for producto in productos:
                                        producto_nombre = f"{producto['producto']} ({producto['cantidad']})".lower()
                                        producto["precio"] = next(
                                            (prod['precio'] for prod in productos_info if prod['producto'].lower() == producto_nombre),
                                            0  
                                        )
                                       

                                    cantidad_cajas = sum([p["cantidad"] for p in productos])
                                    ChatbotService.user_contexts[cuenta_id][sender_id] = context

                                    print(f'productos: {productos}')
                                    print(f'cantidad_cajas: {cantidad_cajas}')
                                    print(f'producto nomnre: {producto_nombre}')
                                    
                                
                                    order_data = schemas.OrderCreate(
                                        phone=telefono,
                                        email=email,
                                        address=direccion,
                                        producto=productos,
                                        cantidad_cajas=cantidad_cajas,
                                        ciudad=ciudad,
                                        ad_id=context.get("ad_id", "N/A"),
                                    )

                                    crud_order = CRUDOrder()
                                    nueva_orden = crud_order.create_order(db=db, order=order_data, nombre=nombre, apellido=apellido)

                                    respuesta = (
                                        f"✅ Su pedido ya quedó registrado:\n"
                                        f"📦 Sus productos llegarán pronto!\n"
                                        f"📞 Teléfono: {telefono}\n"
                                        f"📍 Ciudad: {ciudad}\n"
                                        "El repartidor se comunicará contigo entre 8 AM y 9 PM para confirmar la entrega. ¡Gracias por tu compra! 😊"
                                    )
                                    await FacebookService.send_text_message(sender_id, respuesta, api_key)
                                    context["orden_creada"] = True

                                    ChatbotService.user_contexts[cuenta_id][sender_id] = context
                                    print(f'orden_creada: {context["orden_creada"]}')
                                    logging.info(f"Orden creada exitosamente: {nueva_orden}")

                                except Exception as e:
                                    logging.error(f"Error al crear la orden: {e}")

                        elif context.get("telefono") and context.get("productos") and any(p["cantidad"] > 0 for p in context["productos"]) and context["orden_flujo_aislado"]:
                            print("if con telefono, productos y cantidad mayor a 0")
                            if not context.get("orden_creada"):
                                try:
                                    nombre = context.get("nombre", "Cliente")
                                    apellido = context.get("apellido", "Apellido")
                                    productos = context["productos"]
                                    cantidad_cajas = sum([p["cantidad"] for p in productos])
                                    ciudad = context.get("ciudad", "N/A")
                                    direccion = context.get("direccion", "N/A")
                                    telefono = context.get("telefono")
                                    email = context.get("email", "N/A")

                                    productos_info = crud_producto.get_productos_by_cuenta(db, cuenta_id)

                                    for producto in productos:
                                        producto_nombre = f"{producto['producto']} ({producto['cantidad']})".lower()
                                        producto["precio"] = next(
                                            (prod['precio'] for prod in productos_info if prod['producto'].lower() == producto_nombre),
                                            0  
                                        )

                                    cantidad_cajas = sum([p["cantidad"] for p in productos])
                                    ChatbotService.user_contexts[cuenta_id][sender_id] = context


                                    print(f'productos: {productos}')
                                    print(f'cantidad_cajas: {cantidad_cajas}')

                                    order_data = schemas.OrderCreate(
                                        phone=telefono,
                                        email=email,
                                        address=direccion,
                                        producto=productos,
                                        cantidad_cajas=cantidad_cajas,
                                        ciudad=ciudad,
                                        ad_id=context.get("ad_id", "N/A"),
                                    )

                           
                                    crud_order = CRUDOrder()
                                    nueva_orden = crud_order.create_order(db=db, order=order_data, nombre=nombre, apellido=apellido)

            
                                    respuesta = (
                                        f"✅ Su pedido ya quedó registrado:\n"
                                        f"📦 Sus productos llegarán pronto!\n"
                                        f"📞 Teléfono: {telefono}\n"
                                        f"📍 Ciudad: {ciudad}\n"
                                        "El repartidor se comunicará contigo entre 8 AM y 9 PM para confirmar la entrega. ¡Gracias por tu compra! 😊"
                                    )
                                    await FacebookService.send_text_message(sender_id, respuesta, api_key)
                                    context["orden_creada"] = True

                                    ChatbotService.user_contexts[cuenta_id][sender_id] = context
                                    print(f'orden_creada: {context["orden_creada"]}')
                                    logging.info(f"Orden creada exitosamente: {nueva_orden}")

                                except Exception as e:
                                    logging.error(f"Error al crear la orden: {e}")

                        if context.get("orden_creada"):
                                logging.info("Reiniciando valores después de completar la orden.")
                                keys_to_none = ["direccion", "telefono", "ciudad", "productos"]
                                keys_to_false = ["mensaje_predeterminado_enviado", "mensaje_faltante_enviado", 
                                                "mensaje_creacion_enviado", "mensaje_creacion_enviado2", 
                                                "orden_creada", "orden_flujo_aislado"]
                                for key in keys_to_none:
                                    context[key] = None 
                                for key in keys_to_false:
                                    context[key] = False  
                                context["fase_actual"] = "espera"
                                print(f'keys_to_false: {keys_to_false}')
                                ChatbotService.user_contexts[cuenta_id][sender_id] = context

                                print(f'mensaje_faltante_enviado: {context["mensaje_faltante_enviado"]}')
                                print(f'orden_creada: {context["orden_creada"]}')
                                print(f'orden_flujo_aislado: {context["orden_flujo_aislado"]}')
                                print(f'mensaje_creacion_enviado: {context["mensaje_creacion_enviado"]}')
                                print(f'mensaje_creacion_enviado2: {context["mensaje_creacion_enviado2"]}')
                                print(f'productos: {context["productos"]}')
                                print(f'telefono: {context["telefono"]}')
                                print(f'direccion: {context["direccion"]}')
                                print(f'ciudad: {context["ciudad"]}')
                                return
                    else:
                        # Flujo normal
                        print(f'CONTEXT 2: {context}')
                        print(f'message_text antes de ask_question: {message_text}')
                        if context.get("mensaje_faltante_enviado"):
                            logging.info("habilitando el mensaje faltante")
                            context["mensaje_faltante_enviado"] = False 
                            ChatbotService.user_contexts[cuenta_id][sender_id] = context
                            
                            if context.get("orden_creada"):
                                logging.info("Reiniciando valores después de completar la orden.")
                                keys_to_none = ["direccion", "telefono", "ciudad", "productos"]
                                keys_to_false = ["mensaje_predeterminado_enviado", "mensaje_faltante_enviado", 
                                                "mensaje_creacion_enviado", "mensaje_creacion_enviado2", 
                                                "orden_creada", "orden_flujo_aislado"]
                                for key in keys_to_none:
                                    context[key] = None 
                                for key in keys_to_false:
                                    context[key] = False  
                                context["fase_actual"] = "espera"
                                ChatbotService.user_contexts[cuenta_id][sender_id] = context
                            return
                        
                        else:
                            response_data = await ChatbotService.ask_question(
                                question=message_text,
                                sender_id=sender_id,
                                cuenta_id=cuenta_id,
                                db=db,
                            )
                            response_text = response_data.get("respuesta", "Lo siento, no entendí tu mensaje.")
                            await FacebookService.send_text_message(sender_id, response_text, api_key)
                                                
        return {"status": "OK"}

    @staticmethod
    def get_user_profile(user_id: str, api_key: str):
        """
        Obtiene el perfil de un usuario de Facebook basado en la API Key específica.
        Si ocurre un error o los campos no están disponibles, se devuelven valores predeterminados.
        """
        url = f"https://graph.facebook.com/{user_id}?fields=first_name,last_name&access_token={api_key}"
        try:
            response = requests.get(url, timeout=10) 
            response.raise_for_status()  
            data = response.json()
            first_name = data.get("first_name", "Cliente")
            last_name = data.get("last_name", "Apellido")
            return {"first_name": first_name, "last_name": last_name}

        except requests.exceptions.RequestException as e:
            logging.error(f"Error de conexión al obtener el perfil del usuario: {e}")
        except ValueError as e:
            logging.error(f"Error al procesar la respuesta JSON: {e}")
        except Exception as e:
            logging.error(f"Error inesperado al obtener el perfil del usuario: {e}")

        return {"first_name": "Cliente", "last_name": "Apellido"}

    @staticmethod
    async def send_image_message(recipient_id: str, image_url: str):
        url = f"{settings.FACEBOOK_GRAPH_API_URL}/me/messages"
        headers = {"Content-Type": "application/json"}
        data = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"url": image_url, "is_reusable": True},
                }
            },
            "access_token": settings.FACEBOOK_PAGE_ACCESS_TOKEN,
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Error al enviar el mensaje de imagen.",
            )
        return response.json()


    @staticmethod
    async def send_text_message(recipient_id: str, text: str, api_key: str, cooldown: int = 60):
        """
        Envía un mensaje de texto al usuario en Facebook Messenger, evitando duplicados en un período corto.
        :param recipient_id: ID del receptor en Messenger.
        :param text: Contenido del mensaje.
        :param api_key: Clave de acceso a la API de Facebook.
        :param cooldown: Tiempo en segundos para evitar mensajes duplicados.
        """
        if not text or not text.strip():
            logging.error("Intento de enviar un mensaje vacío. El mensaje no será enviado.")
            raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

        message_key = f"{recipient_id}:{text}"

        current_time = time.time()
        with recent_messages_lock:  
            if message_key in recent_messages:
                last_sent_time = recent_messages[message_key]
                if current_time - last_sent_time < cooldown:
                    logging.info(f"Mensaje duplicado detectado para {recipient_id}. No se enviará.")
                    return {"status": "duplicate", "message": "Mensaje ya enviado recientemente."}


            recent_messages[message_key] = current_time

        url = "https://graph.facebook.com/v12.0/me/messages"
        headers = {"Content-Type": "application/json"}
        data = {"recipient": {"id": recipient_id}, "message": {"text": text}}
        params = {"access_token": api_key}

        response = requests.post(url, headers=headers, json=data, params=params)
        if response.status_code != 200:
            logging.error(f"Error al enviar el mensaje de texto: {response.json()}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error al enviar el mensaje de texto: {response.json()}",
            )

        logging.info(f"Mensaje enviado a {recipient_id}: {text}")
        with recent_messages_lock:
            keys_to_remove = [
                key for key, timestamp in recent_messages.items()
                if current_time - timestamp > cooldown
            ]
            for key in keys_to_remove:
                del recent_messages[key]

        return response.json()
    
    @staticmethod
    def send_message_or_image(recipient_id: str, answer: str):
        image_url_pattern = r"(https?://[^\s]+(\.jpg|\.jpeg|\.png|\.gif))"
        match = re.search(image_url_pattern, answer)

        if match:
            image_url = match.group(0)
            FacebookService.send_image_message(recipient_id, image_url)
        else:
            FacebookService.send_text_message(recipient_id, answer)
    @staticmethod
    def load_api_keys():
        """
        Carga las API Keys desde el archivo api_keys.json.
        """
        if not os.path.exists(FacebookService.API_KEYS_FILE):
            with open(FacebookService.API_KEYS_FILE, "w") as file:
                json.dump({}, file)
        with open(FacebookService.API_KEYS_FILE, "r") as file:
            return json.load(file)

    @staticmethod
    def save_api_keys(api_keys):
        """
        Guarda las API Keys en el archivo api_keys.json.
        """
        with open(FacebookService.API_KEYS_FILE, "w") as file:
            json.dump(api_keys, file)



@router.get("/apikeys/", response_model=List[dict])
async def get_api_keys():
    """
    Devuelve la lista de API Keys configuradas.
    """
    api_keys = FacebookService.load_api_keys()
    return [{"name": name, "key": key} for name, key in api_keys.items()]



@router.post("/apikeys/")
async def create_api_key(api_key: APIKeyCreate):
    """
    Crea una nueva API Key en el archivo api_keys.json.
    """
    api_keys = FacebookService.load_api_keys()
    if api_key.name in api_keys:
        raise HTTPException(status_code=400, detail="El nombre ya existe.")
    api_keys[api_key.name] = api_key.key
    FacebookService.save_api_keys(api_keys)
    return {"message": "API Key creada con éxito"}

@router.delete("/apikeys/{name}")
async def delete_api_key(name: str):
    """
    Elimina una API Key del archivo api_keys.json.
    """
    api_keys = FacebookService.load_api_keys()
    if name not in api_keys:
        raise HTTPException(status_code=404, detail="API Key no encontrada.")
    del api_keys[name]
    FacebookService.save_api_keys(api_keys)
    return {"message": "API Key eliminada con éxito"}

@router.post("/chatbot/ask/")
async def ask_question(
    question: str, cuenta_id: int, db: Session = Depends(get_db)
):
    return await ChatbotService.ask_question(question, cuenta_id, db)


@router.get("/producto/info/")
async def get_product_info(cuenta_id: int, db: Session = Depends(get_db)):
    productos = crud_producto.get_productos_by_cuenta(db, cuenta_id)
    if not productos:
        return {
            "respuesta": "No se encontró información de productos para esta cuenta."
        }

    product_info = "\n".join(
        [f"{prod['producto']}: Precio {prod['precio']} pesos" for prod in productos]
    )
    return {"respuesta": product_info}


@router.post("/facebook/connect/")
async def connect_facebook(account: CuentaSchema, db: Session = Depends(get_db)):
    return await FacebookService.connect_facebook(account, db)


@router.post("/facebook/webhook/", response_model=None)
async def facebook_webhook(request: Request, db: Session = Depends(get_db)):
    return await FacebookService.facebook_webhook(request, db)


@router.get("/facebook/webhook/")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    else:
        raise HTTPException(status_code=403, detail="Token de verificación inválido")
    
    