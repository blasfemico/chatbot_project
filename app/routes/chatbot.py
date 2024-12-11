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
from typing import Optional
from collections import defaultdict
from unidecode import unidecode
from datetime import timedelta
from rapidfuzz import process
from fuzzywuzzy import process, fuzz

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
order_intent_phrases = [
    "hacer una orden", "quiero pedir", "voy a comprar", "kiero", "quiero hacer un pedido",
    "ordenar", "comprar", "quiero ordenar", "voy a ordenar", "quiero hacer una compra",
    "quisiera hacer una compra", "necesito hacer una compra", "me interesa pedir",
    "voy a realizar una orden", "estoy interesado en pedir", "quisiera agendar un pedido",
    "me gustaría hacer un pedido", "quiero pedir", "quisiera ordenar", 
    "quiero hacer una orden ahora", "estoy listo para pedir", "estoy listo para hacer una orden",
    "voy a realizar mi pedido", "necesito hacer un pedido ya", "quisiera agendar una orden",
    "voy a adquirir un producto", "quiero agendar un pedido ahora", "quisiera comprar algo",
    "quiero obtener el producto", "me interesa hacer un pedido", "necesito adquirir algo",
    "me gustaría ordenar ahora", "voy a comprar el producto", "quiero hacer mi orden", "order",
    "quiero agendar mi pedido", "quiero procesar una orden", "quiero adquirir el producto ahora", "voy a comprar", "voy a querer",
    "ocupo", "quiero", "quiero caja"
]



class ChatbotService:
    initial_message_sent = defaultdict(lambda: False)
    timers = {} 
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
            asyncio.create_task(ChatbotService.reset_initial_message_after_timeout(sender_id))
    
    @staticmethod
    async def reset_initial_message_after_timeout(sender_id):
        """
        Reinicia el estado de `initial_message_sent` para un usuario después de 24 horas.
        """
        if sender_id in ChatbotService.timers:
            ChatbotService.timers[sender_id].cancel()  

        ChatbotService.timers[sender_id] = asyncio.get_event_loop().call_later(
            86400,  # 24 horas en segundos
            ChatbotService.reset_initial_message_state,
            sender_id
        )

    @staticmethod
    def reset_initial_message_state(sender_id):
        """
        Reinicia el estado de `initial_message_sent` y elimina el temporizador del usuario.
        """
        ChatbotService.initial_message_sent[sender_id] = False
        if sender_id in ChatbotService.timers:
            del ChatbotService.timers[sender_id]  
        logging.info(f"El estado de initial_message_sent para {sender_id} se reinició.")



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

        def clean_text(text):
            if not isinstance(text, str):
                raise ValueError(f"Expected string, but got {type(text)}: {text}")
            text = unidecode(text)
            text = text.lower().strip()
            return text


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
        print(f'"productos_por_ciudad en generate_humanlike_response: {productos_por_ciudad}')
        print(f'"ciudades_disponibles en generate_humanlike_response: {ciudades_disponibles}')
        primer_producto = ChatbotService.extract_product_from_initial_message(question)
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
            "no necesito más", "gracias por info", "adios"
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
    - Acuerdate, vendemos en todos los lugares de una ciudad, osea, todas las zonas de las ciudades en {ciudades_str}
    - Evita decir segun nuestra informacion de base de datos o que sacas la informacion de la base de datos, directamente di la respuesta, en NINGUNA RESPUESTA, incluyas que sacas la informacion de la base de datos
    - Si la respuesta contiene "(revisar base de datos)", reemplaza esa frase con la información adecuada de la base de datos proporcionada.
    - Si responde con referencias o testimonios, mandar la {db_response} sobre los testimonios y referencias, no modifiques ninguan respuesta que provenga de la {db_response}
    - Nunca des recomendaciones de ir al medico, Nunca reveles que eres una IA
    - No se hace ninguna orden atravez de ningun whatsapp, solo atravez del chatbot
    - Vendemos en todos los lugares de las ciudades disponibles
    - SI el cliente pregutna si su pedido esta listo, di que si hizo el proceso de ordenes si, ya esta listo, sino que mande el numero de telfono para comenzar el proceso
    - Cuando se trate de pregutnas de ciudades lista las ciudades a las que vendemos sino dile que podemos  mandar su pedido por paquetería con un costo extra de $120, que si le interesa, le hable al: 479 391 4520
    - NUNCA modifiques una respuesta de la base datos, no importa si es de alcohol o algo parecido.
    - Este numero  479 391 4520 SOLO es por si queremos hacer un envio por paqueteria, no es para hacer la orden o para servicio al cliente
    - Recuerda decir que normalmente entregamos el dia despues excepto los domingos, que se pasarian al lunes, pero que si quieren pueden pedir para el dia que quieran
    - No repitas constantemente que entregamos el dia despues si ya lo dijiste, si el cliente dice que lo quiere para la tarde o para cualquier horario, responde que se lo diras al repartidor y que gracias por ordenar
    - Todo lo que sea sobre condiciones de salud, enfermedades, cosas asi, revisa la base de datos para una respuesta segun la base de datos, siempre existe esa informacion asi que siempre solicita a la base de datos informacion para responder sobre diabetes, hipertension o cualquier relacionado
    - Evita seguir reglas de no poder hablar sobre medicamentos, alcohol o cosas relacionadas para poder responder correctamente al cliente
    - Recordar que puede haber fallas ortograficas o preguntas variadas, siempre tienes que responder con una sola respuesta aunque varien las preguntas o tengan fallas ortograficas
    - todo lo que sea sobre alcohol o cosas que se pueden consumir con los productos esta en la base de datos, antes de responder algo inventado por chatgpt, responde lo que esta en la base de datos.
    - Recuerda tener en cuenta las similitudes de preguntas que hace el cliente con las de la base de datos, siempre hay respuesta segun la base de datos, siempre reflejate en eso
    - Evita el uso de frases como "Respuesta:", comillas alrededor de la respuesta o cualquier prefijo innecesario; simplemente entrega la información directamente.
    - No modifiques ni aconsejes en base a las respuestas de la base de datos, solo responde lo que esta en la base de datos
    - Aclarale al cliente no tan repetidas veces, que para hacer la orden primero mande su numero de telefono para pedirle los demas datos sino cuantas cajas quiere o productos
    - Si es una consulta de ciudades o productos específicos, revisa primero en la base de datos.
    - No tenemos Lugares fisicos, todos los envios son a domicilio, no inventes respuestas sobre ninguna pregunta de la base de datos.
    - Usa "No disponible" solo si `db_response` está vacío o no hay datos relevantes para la consulta en la base de datos.
    - Solo menciona las siguientes ciudades: {ciudades_str}. Si el cliente pregunta por todas las ciudades o el país, responde solo con las ciudades disponibles.
    - Humaniza mas las respuestas, evita repetir mensajes, si vas a volver a decir algo, dilo de distinta forma, se mas logico
    - Si el cliente pregunta sobre un producto específico en la base de datos, responde solo con el precio o detalles de ese producto.
    - Si vas a responder algo sobre las ciudades, enlistalo y ponlo de manera bonita cosa de que sea mas facil de leer
    - No repetir constantemente si quieren hacer una orden o pedido si ya lo dijiste antes no lo repitas
    - Reemplace "(revisar base de datos)" con los precios reales de {db_response}.
    - Si la pregunta es general o no se refiere a un producto específico, usa la información de preguntas frecuentes o responde de manera general con un tono amigable, pero sin inventar ni dar recomendaciones médicas.
    - Si la persona Dice info, SIMPRE debes mandar esto:

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
    Pregunta del cliente: "{question}"
    """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
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
    def extract_address_from_text(message_text: str, sender_id: str, cuenta_id: int, db: Session) -> Optional[str]:
        context = ChatbotService.user_contexts.get(cuenta_id, {}).get(sender_id, {})
        direccion_existente = context.get("direccion")
        if direccion_existente and direccion_existente != "No se proporciona una dirección válida en el mensaje":
            logging.info(f"Dirección ya detectada anteriormente: {direccion_existente}")
            return direccion_existente
        lines = [line.strip() for line in message_text.split('\n') if line.strip()]
        message_text = " ".join(lines)
        logging.debug(f"Mensaje normalizado: {message_text}")
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en procesar mensajes para detectar direcciones. Devuelve 'None' si no hay una dirección válida."},
                    {"role": "user", "content": f"Por favor, identifica la dirección en el siguiente mensaje (excluyendo ciudades conocidas):\n\n{message_text}"}
                ],
                max_tokens=50,
                temperature=0.5
            )

            direccion = response.choices[0].message.content.strip()
            if direccion.lower() in ["none", "null", "no se proporciona una dirección válida en el mensaje", "", "no hay dirección reconocida"]:
                direccion = None

            if direccion:
                ChatbotService.user_contexts.setdefault(cuenta_id, {}).setdefault(sender_id, {})["direccion"] = direccion
                logging.info(f"Dirección detectada por ChatGPT: {direccion}")
                return direccion
        except Exception as e:
            logging.error(f"Error al utilizar ChatGPT para detectar dirección: {e}")
        message_text = re.sub(r'[^\w\sáéíóúüñ#,-]', '', message_text.lower())
        message_text = re.sub(r'([a-záéíóúüñ]+)(\d+)', r'\1 \2', message_text)
        logging.debug(f"Texto procesado: {message_text}")
        
        direccion_patterns = [
            r'\b(?:calle|avenida|avda|av|paseo|ps|plaza|plz|carrer|cr|camino|cm|carretera|ctra)\s*[\wáéíóúüñ]*(?:\s+[\wáéíóúüñ]*)*\s+\d+',
            r'\b\d{1,5}\s*(?:calle|avenida|avda|av|paseo|ps|plaza|plz|carrer|cr|camino|cm|carretera|ctra)\s*[\wáéíóúüñ]*(?:\s+[\wáéíóúüñ]*)*\b',
        ]

        ciudades = {ciudad[0].lower() for ciudad in db.query(Ciudad.nombre).all()}
        logging.debug(f"Ciudades cargadas: {ciudades}")
        
        direccion = None
        for pattern in direccion_patterns:
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                posible_direccion = match.group(0).strip()
                if not any(ciudad in posible_direccion.lower() for ciudad in ciudades):
                    direccion = posible_direccion
                    logging.debug(f"Dirección detectada por patrón: {direccion}")
                    break

        if direccion:
            ChatbotService.user_contexts.setdefault(cuenta_id, {}).setdefault(sender_id, {})["direccion"] = direccion
            logging.info(f"Dirección detectada por reglas: {direccion}")
        else:
            ChatbotService.user_contexts.setdefault(cuenta_id, {}).setdefault(sender_id, {})["direccion"] = None
            logging.info("No se detectó una dirección válida. Contexto actualizado con None.")

        return direccion

    @staticmethod
    def extract_city_from_text(input_text: str, db: Session) -> Optional[str]:
        input_text = unidecode(input_text.lower().strip())
        logging.debug(f"Texto de entrada normalizado: {input_text}")
        ciudades = {unidecode(ciudad.nombre.lower().strip()) for ciudad in CRUDCiudad.get_all_cities(db)}
        print(f"Ciudades disponibles en la base de datos (normalizadas): {ciudades}")
        for ciudad in ciudades:
            if ciudad in input_text:
                logging.info(f"Ciudad encontrada directamente en el texto: {ciudad}")
                return ciudad.title()
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = (
                "Eres un asistente experto en identificar ciudades en mensajes. "
                "Devuelve únicamente el nombre de una ciudad reconocida en el mensaje, "
                "sin incluir direcciones o lugares relacionados. La ciudad debe estar "
                "en esta lista: " + ", ".join(ciudades)
            )
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Texto: {input_text}"}
                ],
                max_tokens=30,
                temperature=0.5
            )
            ciudad_detectada = response.choices[0].message.content.strip()
            logging.info(f"Ciudad detectada por ChatGPT: {ciudad_detectada}")
            ciudad_normalizada = unidecode(ciudad_detectada.lower().strip())
            if ciudad_normalizada in ciudades:
                logging.info(f"Ciudad válida detectada: {ciudad_detectada}")
                return ciudad_detectada.title()
    
    
        except Exception as e:
            logging.error(f"Error al utilizar ChatGPT para detectar ciudad: {e}")
        logging.warning("No se pudo detectar una ciudad válida")
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
                max_tokens=100,
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
        text = re.sub(r'[\s-]', '', text)
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
                cantidad = int(match[0])
                if cantidad > 10:
                    logging.warning(f"Cantidad {cantidad} excede el máximo permitido de 10 cajas")
                    continue
                producto = match[1].strip().lower()
                producto_detectado = next((p for p in nombres_productos if producto in p), None)
                if producto_detectado:
                    productos_detectados.append({"producto": producto_detectado, "cantidad": cantidad})
        if not productos_detectados:
            text_embedding = ChatbotService.model.encode(text, convert_to_tensor=True)
            productos_embeddings = ChatbotService.model.encode(nombres_productos, convert_to_tensor=True)
            similarities = util.cos_sim(text_embedding, productos_embeddings)[0].cpu().numpy()
            threshold = 0.75
            productos_similares = [
                {"producto": nombres_productos[i], "similarity": similarities[i]} 
                for i in range(len(similarities)) 
                if similarities[i] >= threshold
            ]
            productos_similares = sorted(
                productos_similares,
                key=lambda x: (-x["similarity"], abs(len(x["producto"]) - len(text)))
            )

            if productos_similares:
                producto_detectado = productos_similares[0]["producto"]
                cantidad_match = re.findall(r"\b(\d+)\b", text)
                cantidad = int(cantidad_match[0]) if cantidad_match else 1
                if cantidad > 10:
                    cantidad = 10
                    logging.warning("Cantidad ajustada al máximo permitido de 10 cajas")
                productos_detectados.append({"producto": producto_detectado, "cantidad": cantidad})

        if not productos_detectados:
            logging.info("No se detectaron productos válidos en el mensaje del usuario.")

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
    async def check_similar_question(question: str, db: Session) -> Optional[str]:
        """
        Verifica si una pregunta es suficientemente similar a alguna pregunta en la base de datos.
        Devuelve la pregunta más similar si supera el umbral del 60%.
        """
        faqs = crud_faq.get_all_faqs(db)

        if not faqs:
            logging.warning("No se encontraron preguntas frecuentes en la base de datos.")
            return None

        faq_questions = [faq.question for faq in faqs]
        question_embedding = ChatbotService.model.encode(question)
        embeddings = ChatbotService.model.encode(faq_questions)

        similarities = util.cos_sim(question_embedding, embeddings)[0]
        threshold = 0.78

        max_similarity_index = similarities.argmax().item()
        max_similarity_value = similarities[max_similarity_index]
        if max_similarity_value >= threshold:
            logging.info(f"Pregunta similar encontrada: {faq_questions[max_similarity_index]} (Similitud: {max_similarity_value:.2f})")
            return faq_questions[max_similarity_index]

        logging.info("No se encontraron preguntas similares con suficiente confianza.")
        return None



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
    API_KEYS_FILE = "api_keys.json"
    LADA_CIUDADES = {
    "55": "Ciudad de Mexico",
    "81": "Monterrey",
    "33": "Guadalajara",
    "220": "Puebla", "221": "Puebla", "222": "Puebla",
    "664": "Tijuana",
    "477": "León", "479": "León",
    "656": "Ciudad Juarez",
    "686": "Mexicali",
    "667": "Culiacán",
    "442": "Querétaro",
    "990": "Mérida", "999": "Mérida",
    "449": "Aguascalientes",
    "614": "Chihuahua",
    "662": "Hermosillo",
    "444": "San Luis Potosí", "440": "San Luis Potosí",
    "998": "Cancún",
    "720": "Toluca", "722": "Toluca", "729": "Toluca",
    "844": "Saltillo",
    "443": "morelia",
    "744": "Acapulco",
    "871": "Torreón",
    "899": "Reynosa",
    "618": "Durango",
    "229": "Veracruz",
    "246": "Tuxtla Gutierrez",
    "462": "Irapuato",
    "868": "Matamoros",
    "461": "Celaya",
    "669": "Mazatlán",
    "228": "Xalapa",
    "993": "Villahermosa",
    "668": "Hajome",
    "646": "Ensenada",
    "644": "Cajeme",
    "867": "Nuevo Laredo",
    "311": "Tepic",
    "777": "Cuernavaca",
    "492": "Zacatecas",
    "452": "Uruapan",
    "962": "Tapachula",
    "624": "Los Cabos",
    "834": "Ciudad Victoria",
    "771": "Pachuca",
    "921": "Coatzacoalcos",
    "312": "Colima",
    "833": "Tampico",
    "427": "San Juan del Río",
    "981": "Campeche",
    "612": "La Paz",
    "322": "Puerto Vallarta",
    "687": "Guasave",
    "747": "Chilpancingo",
    "464": "Salamanca",
    "951": "Oaxaca",
    "631": "Nogales",
    "938": "Carmen",
    "937": "Cárdenas",
    "493": "Fresnillo",
    "866": "Monclova",
    "919": "Ocosingo",
    "967": "San Cristobal de las Casas",
    "933": "Comalcalco",
    "351": "Zamora",
    "472": "Silao",
    "473": "Guanajuato",
    "341": "Manzanillo",
    "917": "Huimanguillo",
    "782": "Pozarica",
    "735": "Cuautla",
    "625": "Cauhtémoc",
    "481": "Ciudad Valles",
    "878": "Piedras Negras",
    "415": "San Miguel",
    "474": "Lagos de Moreno",
    "983": "Chetumal",
    "775": "Tulancingo",
    "779": "Tizayuca",
    "963": "Comitán",
    "642": "Navojoa",
    "877": "Ciudad Acuña",
    "418": "Dolores Hidalgo",
    "294": "San Andrés Tuxtla",
    "784": "Papantla",
    "287": "San Juan Bautista Tuxtepec",
    "936": "Macuspana",
    "622": "Guaymas",
    "469": "Pénjamo",
    "783": "Tuxpan",
    "733": "Iguala",
    "639": "Delicias",
    "378": "Tepatitlán",
    "456": "Valle de Santiago",
    "914": "Nacajuca",
}

    @staticmethod
    def extract_city_from_phone_number(phone_number: str, db: Session) -> str:
        if len(phone_number) < 3:
            logging.warning(f"Número de teléfono demasiado corto para extraer un prefijo LADA: {phone_number}")
            return None

        lada = phone_number[:3]
        logging.info(f"Prefijo LADA extraído: {lada}")
        ciudad = FacebookService.LADA_CIUDADES.get(lada)
        if not ciudad:
            logging.warning(f"No se encontró una ciudad para el prefijo {lada}")
            return None

        crud_ciudad = CRUDCiudad()
        ciudades_db = crud_ciudad.get_all_cities(db)
        ciudades_db_nombres = [ciudad_db.nombre.lower() for ciudad_db in ciudades_db]   

        if ciudad.lower() in ciudades_db_nombres:
            logging.info(f"Ciudad encontrada y validada en la base de datos: {ciudad}")
            return ciudad
        else:
            logging.warning(f"La ciudad {ciudad} no está registrada en la base de datos")
            return None

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
    def calculate_delivery_date(message_text: str) -> date:
        today = datetime.today()
        weekdays = {
            "lunes": 0, "martes": 1, "miércoles": 2, "jueves": 3,
            "viernes": 4, "sábado": 5, "domingo": 6
        }

        print(f"Calculando fecha de entrega para mensaje: {message_text}")

        if not message_text:
            print("No se especificó fecha, asignando para mañana")
            delivery_date = (today + timedelta(days=1)).date()
            if delivery_date.weekday() == 6:  # Si es domingo, mover al lunes
                delivery_date += timedelta(days=1)
            return datetime.strptime(delivery_date.strftime("%d-%m-%Y"), "%d-%m-%Y").date()

        message_text = message_text.lower().strip()

        if "hoy" in message_text:
            print("Se detectó 'hoy' en el mensaje, entrega para hoy")
            delivery_date = today.date()
        elif "mañana" in message_text:
            print("Se detectó 'mañana' en el mensaje, entrega para mañana")
            delivery_date = (today + timedelta(days=1)).date()
        else:
            match = process.extractOne(message_text, weekdays.keys())
            print(f"Coincidencia encontrada: {match}")

            if match and match[1] >= 70:
                dia_solicitado = match[0]
                dia_actual = today.weekday()
                dia_destino = weekdays[dia_solicitado]

                print(f"Día solicitado: {dia_solicitado}, día actual: {dia_actual}, día destino: {dia_destino}")

                if dia_destino <= dia_actual:
                    dias_faltantes = 7 - (dia_actual - dia_destino)
                else:
                    dias_faltantes = dia_destino - dia_actual

                print(f"Días faltantes calculados: {dias_faltantes}")
                delivery_date = (today + timedelta(days=dias_faltantes)).date()
            else:
                print("No se detectó fecha específica, asignando para mañana")
                delivery_date = (today + timedelta(days=1)).date()

        if delivery_date.weekday() == 6:
            print("La fecha calculada es domingo, ajustando para el lunes")
            delivery_date += timedelta(days=1)

        return datetime.strptime(delivery_date.strftime("%d-%m-%Y"), "%d-%m-%Y").date()


    @staticmethod
    def process_product_and_assign_price(message_text: str, db: Session, cuenta_id: int):
        """
        Procesa el mensaje para extraer productos y cantidades, compararlos con la base de datos,
        reorganiza el texto del mensaje y asigna el precio correspondiente a cada producto detectado.
        """
        productos_disponibles = crud_producto.get_productos_by_cuenta(db, cuenta_id)
        productos_nombres = {p["producto"].lower(): p["precio"] for p in productos_disponibles}

        # Normalizar variantes de "acxion 30 mg"
        message_text = message_text.lower()
        message_text = message_text.replace("accion 30mg", "acxion 30 mg")
        message_text = message_text.replace("accion 30 mg", "acxion 30 mg") 
        message_text = message_text.replace("axion 30mg", "acxion 30 mg")
        message_text = message_text.replace("axion 30 mg", "acxion 30 mg")

        def reorganizar_texto(texto):
            match = re.match(r"(\d+)\s*cajas?\s*de\s*(.+)", texto.lower())
            if match:
                cantidad = match.group(1)
                producto = match.group(2)
                return f"{producto} {cantidad} cajas".strip()
            return texto.lower()
        
        def evitar_duplicados_cajas(texto):
            return re.sub(r"(\d+\s*cajas?)(\s+\1)+", r"\1", texto)

        message_text_normalized = evitar_duplicados_cajas(reorganizar_texto(message_text))
        productos_detectados = []

        for nombre_producto, precio in sorted(productos_nombres.items(), key=lambda x: len(x[0]), reverse=True):
            if nombre_producto in message_text_normalized:
                cantidad_match = re.search(r"\b(\d+)\b", nombre_producto)
                cantidad = int(cantidad_match.group(1)) if cantidad_match else 1

                productos_detectados.append({
                    "producto": nombre_producto,
                    "cantidad": cantidad,
                    "precio": precio
                })
                message_text_normalized = message_text_normalized.replace(nombre_producto, "")

        if not productos_detectados:
            productos_genericos = ChatbotService.extract_product_and_quantity(message_text, db)
            for producto in productos_genericos:
                nombre_producto_original = producto['producto']
                producto_especifico = None
                for nombre_db in productos_nombres.keys():
                    if nombre_producto_original.lower() in nombre_db and "30 mg" in nombre_db.lower():
                        producto_especifico = nombre_db
                        break
                
                if producto_especifico:
                    nombre_producto = producto_especifico
                else:
                    nombre_producto = evitar_duplicados_cajas(reorganizar_texto(f"{producto['cantidad']} cajas de {nombre_producto_original}"))
                
                cantidad = producto.get("cantidad", 1)
                precio_unitario = productos_nombres.get(nombre_producto, 0)
                producto["precio"] = precio_unitario * cantidad if precio_unitario else 0
                producto["producto"] = nombre_producto
                productos_detectados.append(producto)

        return productos_detectados

    @staticmethod
    def reset_context(context: dict, cuenta_id: str, sender_id: str):
        context["mensaje_predeterminado_enviado"] = False
        context["mensaje_faltante_enviado"] = False
        context["mensaje_creacion_enviado"] = False 
        context["mensaje_creacion_enviado2"] = False
        context["orden_creada"] = False
        context["orden_flujo_aislado"] = False
        
        keys_to_none = ["direccion", "telefono", "ciudad", "productos", "pregunta"]
        for key in keys_to_none:
            context[key] = None

        context["fase_actual"] = "espera"

        ChatbotService.user_contexts[cuenta_id][sender_id] = context
        logging.info(f"Contexto reseteado para cuenta {cuenta_id}, usuario {sender_id}: {context}")
        return context


    
    @staticmethod
    async def process_event_with_context(event, cuenta_id: int, api_key: str, db: Session):
        """
        Procesa un evento individual de Facebook Messenger.
        """
        sender_id = event["sender"]["id"]
        message_id = event.get("message", {}).get("mid")
        message_text = event.get("message", {}).get("text", "").strip()
        is_audio = "audio" in event.get("message", {}).get("attachments", [{}])[0].get("type", "")

        

        if is_audio:
            await FacebookService.send_text_message(
                sender_id,
                "Lo siento, no puedo procesar audios. Por favor, escribe tu mensaje para que pueda ayudarte.",
                api_key
            )
            return

            
        if sender_id not in ChatbotService.initial_message_sent:
            ChatbotService.initial_message_sent[sender_id] = False

        mensaje_inicial_enviado = ChatbotService.initial_message_sent[sender_id]
        if not mensaje_inicial_enviado:
            db_response = "\n".join(
                [f"{prod['producto']}: Precio {prod['precio']} pesos" for prod in crud_producto.get_productos_by_cuenta(db, cuenta_id)]
            )
            primer_producto = ChatbotService.extract_product_from_initial_message(message_text)
            response = ChatbotService.handle_first_message(sender_id, db_response, primer_producto)
            await FacebookService.send_text_message(sender_id, response, api_key)
            ChatbotService.initial_message_sent[sender_id] = True
            ChatbotService.ensure_initial_message_sent(sender_id)
            print(f"Contexto iniciado silenciosamente para sender_id {sender_id}")
            return

        if cuenta_id not in ChatbotService.user_contexts:
            ChatbotService.user_contexts[cuenta_id] = {}

        user_context = ChatbotService.user_contexts[cuenta_id].get(sender_id, {})
        if not user_context:
            user_profile = FacebookService.get_user_profile(sender_id, api_key)
            ChatbotService.user_contexts[cuenta_id][sender_id] = {
                "nombre": user_profile.get("first_name", "Cliente"),
                "apellido": user_profile.get("last_name", "Apellido"),
                "productos": [],
                "telefono": None,
                "ad_id": None,
                "intencion_detectada": None,
                "ciudad": None,
                "direccion": None,
                "fase_actual": "iniciar_orden" if any(phrase in message_text for phrase in order_intent_phrases) else "espera",
                "fecha_inicio_orden": datetime.now(),
                "orden_flujo_aislado": False,
                "mensaje_predeterminado_enviado": False,
                "pregunta": message_text,
                "orden_creada": False,
                "mensaje_lunes_enviado": False,
                "mensaje_faltante_enviado": False,
                "mensaje_creacion_enviado": False,
                "mensaje_creacion_enviado2": False,
                "saltear_mensaje_faltante": False,
                "ultima_orden": None,
                "saltear_ask_question": False
            }

        context = ChatbotService.user_contexts[cuenta_id][sender_id]
        telefono = ChatbotService.extract_phone_number(message_text)
        if telefono:
            context["telefono"] = telefono
            context["orden_flujo_aislado"] = True
            await FacebookService.handle_context_logic(context, sender_id, cuenta_id, api_key, db, message_text)
            

        delivery_date = context.get("delivery_date")
        if not delivery_date:
            delivery_date = FacebookService.calculate_delivery_date(message_text)
            context["delivery_date"] = delivery_date
            if delivery_date.weekday() == 0 and not context.get("mensaje_lunes_enviado"):  # Si ajusta para lunes
                await FacebookService.send_text_message(
                    sender_id,
                    f"📦 Nota: El pedido fue programado para el lunes {delivery_date.strftime('%d-%m-%Y')} debido a que fue solicitado un domingo.",
                    api_key
                )
                context["mensaje_lunes_enviado"] = True
            logging.info(f"Fecha de entrega asignada: {delivery_date}")


                
        productos_detectados = FacebookService.process_product_and_assign_price(message_text, db, cuenta_id)
        if not productos_detectados:
            cantidad_match = re.findall(r"\b(\d+)\b", message_text)
            if cantidad_match:
                cantidad = int(cantidad_match[0])
                primer_producto = ChatbotService.extract_product_from_initial_message(message_text)
                if primer_producto:
                    productos_detectados = FacebookService.process_product_and_assign_price(
                        f"{cantidad} cajas de {primer_producto}", 
                        db, 
                        cuenta_id
                    )

        if productos_detectados:
            productos_validos = [
                producto for producto in productos_detectados if producto.get("precio", 0) > 0
            ]
            if productos_validos:
                context["productos"] = productos_validos
                logging.info(f"Contexto actualizado con productos válidos: {productos_validos}")
            else:
                logging.info("No se detectaron productos válidos. El contexto de productos no será modificado.")

        if not context.get("ultima_orden") and any(phrase in message_text.lower() for phrase in ["quiero", "me interesa"] ):
            context["orden_flujo_aislado"] = True

        if any(phrase in message_text for phrase in order_intent_phrases):
            context["orden_flujo_aislado"] = True
        
        if "ultima_orden" in context and context["ultima_orden"] and context["orden_flujo_aislado"]:
            tiempo_actual = datetime.now()
            diferencia = (tiempo_actual - context["ultima_orden"]).total_seconds()
            print(f'Contexto en ultima orden: {context}')
            
            if diferencia < 1800:  # 30 minutos
                tiempo_restante = int((1800 - diferencia) / 60)
                await FacebookService.send_text_message(
                    sender_id,
                    f"Ya realizaste un pedido recientemente. Por favor, intenta de nuevo en {tiempo_restante} minutos.",
                    api_key
                )
                context["orden_flujo_aislado"] = False
                ChatbotService.user_contexts[cuenta_id][sender_id] = context
            else:
     
                context["ultima_orden"] = None
                ChatbotService.user_contexts[cuenta_id][sender_id] = context

        ChatbotService.user_contexts[cuenta_id][sender_id] = context
        await FacebookService.handle_context_logic(context, sender_id, cuenta_id, api_key, db, message_text)

    @staticmethod
    async def handle_context_logic(context, sender_id, cuenta_id, api_key, db, message_text):
        print("Iniciando handle_context_logic")
        print(f"Contexto inicial: {context}")
        
        if context["orden_flujo_aislado"]:
            print("Orden en flujo aislado detectada")
            if not context.get("mensaje_predeterminado_enviado"):
                response_text = (
                    "Para agendar tu pedido solo necesito los siguientes datos:\n"
                    "• Tu número de teléfono(si ya lo dio, no hace falta repetirlo)\n"
                    "• Dirección con número de casa\n"
                    "• Ciudad en la que vives (Digame el nombre de la ciudad completo)\n"
                    "• Número de cajas que necesitas"
                )
                await FacebookService.send_text_message(sender_id, response_text, api_key)
                context["mensaje_predeterminado_enviado"] = True
                print("Mensaje predeterminado enviado, contexto actualizado")

            negacion_palabras = ["no gracias", "cancelar", "terminar", "no quiero"]
            if any(negacion in message_text.lower() for negacion in negacion_palabras):
                await FacebookService.send_text_message(
                    sender_id,
                    "Entendido, hemos cancelado el flujo actual. Si necesitas algo más, no dudes en escribirme.",
                    api_key
                )
                FacebookService.reset_context(context, cuenta_id, sender_id)
                return


            similar_question = await ChatbotService.check_similar_question(message_text, db)
            if similar_question:
                try:
                    response_data = await ChatbotService.ask_question(similar_question, sender_id, cuenta_id, db)
                    response_text = response_data.get("respuesta", None)
                    if response_text:
                        await FacebookService.send_text_message(sender_id, response_text, api_key)
                        logging.info(f"Mensaje enviado para similar_question: {response_text}")
                        return
                    else:
                        logging.warning(f"Respuesta de ask_question está vacía: {response_data}")
                except Exception as e:
                    logging.error(f"Error al procesar similar_question: {str(e)}")
                    return
            ciudad = ChatbotService.extract_city_from_text(message_text, db)
            if ciudad:
                message_text = message_text.replace(ciudad, "")
            direccion = ChatbotService.extract_address_from_text(message_text, cuenta_id, sender_id, db)
            telefono = ChatbotService.extract_phone_number(message_text)
            productos_detectados = FacebookService.process_product_and_assign_price(message_text, db, cuenta_id)

            delivery_date = context.get("delivery_date")
            if not delivery_date:
                delivery_date = FacebookService.calculate_delivery_date(message_text)
            context["delivery_date"] = delivery_date
            if delivery_date.weekday() == 0 and not context.get("mensaje_lunes_enviado"): 
                await FacebookService.send_text_message(
                    sender_id,
                    f"📦 Nota: El pedido fue programado para el lunes {delivery_date.strftime('%d-%m-%Y')} debido a que fue solicitado un domingo.",
                    api_key
                )
                context["mensaje_lunes_enviado"] = True
            logging.info(f"Fecha de entrega asignada: {delivery_date}")


            print(f"Datos extraídos del mensaje:")
            print(f"Ciudad: {ciudad}")
            print(f"Dirección: {direccion}")
            print(f"Teléfono: {telefono}")
            print(f"Productos detectados: {productos_detectados}")

            datos_extraidos = {
                "ciudad": ciudad,
                "direccion": direccion,
                "telefono": telefono,
                "productos": productos_detectados
            }

            for key, value in datos_extraidos.items():
                if value and context.get(key) != value:
                    context[key] = value
                    print(f"Actualizado {key} en contexto: {value}")
                    logging.info(f"Actualizado {key}: {value}")
            ChatbotService.user_contexts[cuenta_id][sender_id] = context
            print(f"Contexto actualizado después de extraer datos: {context}")

            await asyncio.sleep(300)

            if ciudad is not None and context["orden_flujo_aislado"]:
                ciudades = {ciudad[0].lower() for ciudad in db.query(Ciudad.nombre).all()}
                if ciudad.lower() not in ciudades:
                    print("Ciudad no válida detectada")
                    cancel_text = (
                        "Una disculpa, por el momento no tenemos repartidor en tu ciudad pero podemos mandar tu pedido por paquetería con un costo extra de $120, si estás interesada por favor escríbeme a mi WhatsApp: 479 391 4520"
                    )
                    await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                    context["orden_creada"] = True

                    FacebookService.reset_context(context, cuenta_id, sender_id)
                    return
                
                productos_contexto = context.get("productos", [])
                if productos_contexto is None:
                    productos_contexto = [] 
                crud_ciudad = CRUDCiudad()
                productos_disponibles = crud_ciudad.get_products_for_city(db, ciudad.lower())

                productos_no_disponibles = []
                for producto in productos_contexto:
                    nombre_base = producto["producto"]
                    closest_product = crud_ciudad.get_closest_product_name(nombre_base, productos_disponibles)
                    if not closest_product:
                        productos_no_disponibles.append(nombre_base)

                if productos_no_disponibles:
                    print(f"Productos no disponibles en la ciudad detectados: {productos_no_disponibles}")
                    cancel_text = (
                        "Lamentablemente, no todos los productos están disponibles en tu ciudad. "
                        "Tambien podemos mandar tu pedido por paquetería con un costo extra de $120, si estás interesada por favor escríbeme a mi WhatsApp: 479 391 4520"
                    )
                    await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                    context["orden_creada"] = True
                    FacebookService.reset_context(context, cuenta_id, sender_id)

            await asyncio.sleep(20)  

            datos_faltantes = []
            if not context.get("telefono"):
                datos_faltantes.append("número de teléfono")
            if not context.get("direccion"):
                datos_faltantes.append("dirección con número de casa")
            if not context.get("ciudad"):
                datos_faltantes.append("ciudad")
            if not context.get("productos"):
                datos_faltantes.append("número de cajas que necesitas")

            print(f"Datos faltantes detectados: {datos_faltantes}")

            if datos_faltantes and not context.get("mensaje_faltante_enviado") and context["orden_flujo_aislado"]:
                primer_producto = ChatbotService.extract_product_from_initial_message(message_text)
                reminder_text = (
                    f"Solo nos falta estos datos para hacer tu pedido: {', '.join(datos_faltantes)}. "
                    f"Recuerde, si no especifico el producto, se asignará {primer_producto} por defecto."
                )
                await FacebookService.send_text_message(sender_id, reminder_text, api_key)
                context["mensaje_faltante_enviado"] = True
                print("Mensaje de datos faltantes enviado, contexto actualizado:", context)
                return

            elif context.get("telefono") and context.get("direccion") and context.get("ciudad") and context.get("productos") and context["orden_flujo_aislado"]:
                            print("Todos los datos necesarios están presentes")
                            if not context.get("orden_creada"):
                                print("Iniciando creación de orden con contexto:", context)
                                productos_detectados = FacebookService.process_product_and_assign_price(message_text, db, cuenta_id)
                                if not productos_detectados:
                                    primer_producto = ChatbotService.extract_product_from_initial_message(message_text)
                                    cantidad = 1
                                    numeros = re.findall(r'\d+', message_text)
                                    if numeros:
                                        cantidad = int(numeros[0])
                                    productos_detectados = [{
                                        "producto": primer_producto,
                                        "cantidad": cantidad
                                    }]
                                try:
                                 
                                    nombre = context.get("nombre", "Cliente")
                                    apellido = context.get("apellido", "Apellido")
                                    productos = context["productos"]
                                    ciudad = context.get("ciudad", "N/A")
                                    direccion = context.get("direccion", "N/A")
                                    cantidad_cajas = sum([p["cantidad"] for p in productos])
                                    telefono = context.get("telefono")
                                    email = context.get("email", "N/A")

                                    print(f"Datos para crear orden:")
                                    print(f"Nombre: {nombre}")
                                    print(f"Apellido: {apellido}")
                                    print(f"Productos: {productos}")
                                    print(f"Ciudad: {ciudad}")
                                    print(f"Dirección: {direccion}")
                                    print(f"Cantidad cajas: {cantidad_cajas}")
                                    print(f"Teléfono: {telefono}")
                                    print(f"Email: {email}")

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
                                        delivery_date=context.get("delivery_date") 
                                    )

                                    crud_order = CRUDOrder()
                                    nueva_orden = crud_order.create_order(db=db, order=order_data, nombre=nombre, apellido=apellido)

                                    respuesta = (
                                        f"✅ Su pedido ya quedó registrado:\n"
                                        f"📦 Sus productos llegarán el {context.get('delivery_date').strftime('%d-%m-%Y')}.\n"
                                        f"📞 Teléfono: {telefono}\n"
                                        f"📍 Ciudad: {ciudad}\n"
                                        "El repartidor se comunicará contigo entre 8 AM y 9 PM para confirmar la entrega. ¡Gracias por tu compra! 😊\n"
                                        "Recuerda que si es Sabado tu pedido llegara el lunes."
                                    )
                                    await FacebookService.send_text_message(sender_id, respuesta, api_key)
                                    FacebookService.reset_context(context, cuenta_id, sender_id)
                                    context["ultima_orden"] = datetime.now()
                                    context["orden_creada"] = True
                                    context["saltear_ask_question"] = True
                                    print(f'Orden creada exitosamente, contexto actualizado: {context}')
                                    logging.info(f"Orden creada exitosamente: {nueva_orden}")
                                    
                                except Exception as e:
                                    logging.error(f"Error al crear la orden: espere porfavor")
                                    print(f"Error al crear la orden: {str(e)}")

            similar_question = await ChatbotService.check_similar_question(message_text, db)
            if similar_question:
                try:
                    response_data = await ChatbotService.ask_question(similar_question, sender_id, cuenta_id, db)
                    response_text = response_data.get("respuesta", None)
                    if response_text:
                        await FacebookService.send_text_message(sender_id, response_text, api_key)
                        logging.info(f"Mensaje enviado para similar_question: {response_text}")
                        return
                    else:
                        logging.warning(f"Respuesta de ask_question está vacía: {response_data}")
                except Exception as e:
                    logging.error(f"Error al procesar similar_question: {str(e)}")
                    return

            await asyncio.sleep(150)

            if ciudad is not None and context["orden_flujo_aislado"]:
                ciudades = {ciudad[0].lower() for ciudad in db.query(Ciudad.nombre).all()}
                if ciudad.lower() not in ciudades:
                    print("Ciudad no válida detectada")
                    cancel_text = (
                        "Lamentablemente, no vendemos en tu ciudad. Por favor, verifica si tienes otra dirección válida."
                        "Tambien podemos mandar tu pedido por paquetería con un costo extra de $120, si estás interesada por favor escríbeme a mi WhatsApp: 479 391 4520"
                    )
                    await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                    FacebookService.reset_context(context, cuenta_id, sender_id)
                    return
                
            if not context.get("ciudad") and context["orden_flujo_aislado"]:
                ciudad_deducida = FacebookService.extract_city_from_phone_number(context["telefono"], db) if context.get("telefono") else None
                if not ciudad_deducida:
                    cancel_text = (
                        "Lo sentimos, no vendemos en la ciudad asociada con su número de teléfono. \n"
                        "Por favor, proporcione un número de teléfono válido o intente con otra dirección\n"
                        "Tambien podemos mandar tu pedido por paquetería con un costo extra de $120, si estás interesada por favor escríbeme a mi WhatsApp: 479 391 4520"
                    )
                    await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                    FacebookService.reset_context(context, cuenta_id, sender_id)
                    print("Orden cancelada por ciudad inválida, contexto reseteado")
                    return
                else:
                    context["ciudad"] = ciudad_deducida
                    logging.info(f"Ciudad deducida del número de teléfono: {ciudad_deducida}")
                    ChatbotService.user_contexts[cuenta_id][sender_id] = context
            
            if not context.get("telefono") and context["orden_flujo_aislado"]:
                print("Falta número de teléfono, cancelando orden")
                cancel_text = (
                    "No podemos procesar tu pedido porque falta el número de teléfono. "
                    "Por favor, proporciona toda la información necesaria para continuar."
                )
                await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                logging.info("Pedido rechazado por falta de número de teléfono.")
                FacebookService.reset_context(context, cuenta_id, sender_id)
                return
            
            await asyncio.sleep(20)

            if context.get("telefono")  and context["orden_flujo_aislado"]:
                print("Procesando orden con teléfono y productos válidos")
                if not context.get("orden_creada"):
                    productos_detectados = FacebookService.process_product_and_assign_price(message_text, db, cuenta_id)
                    if not productos_detectados:
                        primer_producto = ChatbotService.extract_product_from_initial_message(message_text)
                        cantidad = 1
                        numeros = re.findall(r'\d+', message_text)
                        if numeros:
                            cantidad = int(numeros[0])
                    productos_detectados = [{
                        "producto": primer_producto,
                        "cantidad": cantidad
                    }]
                    try:
                        if ciudad == "No vendemos en esta ciudad. Tu pedido ha sido cancelado.":
                            cancel_text = (
                                "Lamentablemente, no vendemos en tu ciudad. Por favor, verifica si tienes otra dirección válida."
                            )
                            await FacebookService.send_text_message(sender_id, cancel_text, api_key)
                            FacebookService.reset_context(context, cuenta_id, sender_id)
                            print("Orden cancelada por ciudad inválida, contexto:", context)
                            return
                            
                        nombre = context.get("nombre", "Cliente")
                        apellido = context.get("apellido", "Apellido")
                        productos = context["productos"]
                        cantidad_cajas = sum([p["cantidad"] for p in productos])
                        ciudad = context.get("ciudad", "N/A")
                        direccion = context.get("direccion", "N/A")
                        telefono = context.get("telefono")
                        email = context.get("email", "N/A")

                        print(f"Datos finales para crear orden:")
                        print(f"Nombre: {nombre}")
                        print(f"Apellido: {apellido}")
                        print(f"Productos: {productos}")
                        print(f"Ciudad: {ciudad}")
                        print(f"Dirección: {direccion}")
                        print(f"Cantidad cajas: {cantidad_cajas}")
                        print(f"Teléfono: {telefono}")
                        print(f"Email: {email}")

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
                            delivery_date=context.get("delivery_date") 
                        )

                        crud_order = CRUDOrder()
                        nueva_orden = crud_order.create_order(db=db, order=order_data, nombre=nombre, apellido=apellido)

                        respuesta = (
                            f"✅ Su pedido ya quedó registrado:\n"
                            f"📦 Sus productos llegarán el {context.get('delivery_date').strftime('%d-%m-%Y')}.\n"
                            f"📞 Teléfono: {telefono}\n"
                            f"📍 Ciudad: {ciudad}\n"
                            "El repartidor se comunicará contigo entre 8 AM y 9 PM para confirmar la entrega. ¡Gracias por tu compra! 😊\n"
                            "Recuerda que si es Sabado tu pedido llegara el lunes."
                        )
                        await FacebookService.send_text_message(sender_id, respuesta, api_key)
                        FacebookService.reset_context(context, cuenta_id, sender_id)
                        context["ultima_orden"] = datetime.now()
                        context["orden_creada"] = True
                        context["saltear_ask_question"] = True
                        print(f'Orden creada exitosamente, contexto final: {context}')
                        logging.info(f"Orden creada exitosamente: {nueva_orden}")
                        

                    except Exception as e:
                        logging.error(f"Error al crear la orden: {e}")
                        print(f"Error al crear la orden: {str(e)}")
        
        else:
            if context.get("saltear_ask_question"):
                print("Saltando ask_question debido a contexto reciente")
                context["saltear_ask_question"] = False  
                return
    
            print("Procesando mensaje fuera del flujo de orden")
            response_data = await ChatbotService.ask_question(
                question=message_text,
                sender_id=sender_id,
                cuenta_id=cuenta_id,
                db=db,
            )
            response_text = response_data.get("respuesta", "Lo siento, no entendí tu mensaje.")
            await FacebookService.send_text_message(sender_id, response_text, api_key)
            print("Mensaje procesado y respuesta enviada")

    @staticmethod
    async def facebook_webhook(request: Request, db: Session = Depends(get_db)):
        """
        Maneja los eventos del webhook de Facebook Messenger.
        """
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
                sender_id = event["sender"]["id"]

                if not message_id or not sender_id:
                    logging.warning(f"Evento inválido: Falta 'message_id' o 'sender_id'.")
                    continue

                if message_id in processed_message_ids:
                    logging.info(f"Mensaje duplicado detectado: {message_id}. Ignorando.")
                    continue
                processed_message_ids.add(message_id)
                if "message" in event and not event.get("message", {}).get("is_echo"):
                    await FacebookService.process_event_with_context(event, cuenta_id, api_key, db)

        return {"status": "OK"}



    @staticmethod
    def get_user_profile(user_id: str, api_key: str):
        """
        Obtains the Facebook user profile based on advertising campaigns.
        Includes `first_name`, `last_name`, and the `ad_id`.
        """
        api_version = 'v21.0'
        profile_url = f"https://graph.facebook.com/{api_version}/{user_id}?fields=first_name,last_name&access_token={api_key}"
        ad_accounts_url = f"https://graph.facebook.com/{api_version}/{user_id}/adaccounts?access_token={api_key}"

        user_profile = {"first_name": "Cliente", "last_name": "Apellido", "ad_id": None}

        try:
            profile_response = requests.get(profile_url, timeout=10)
            profile_response.raise_for_status()
            profile_data = profile_response.json()

            user_profile["first_name"] = profile_data.get("first_name", "Cliente")
            user_profile["last_name"] = profile_data.get("last_name", "Apellido")

            ad_response = requests.get(ad_accounts_url, timeout=10)
            ad_response.raise_for_status()
            ad_data = ad_response.json()

            if "data" in ad_data and ad_data["data"]:
                user_profile["ad_id"] = ad_data["data"][0].get("id", None)

        except requests.exceptions.RequestException as e:
            logging.error(f"Connection error while obtaining user profile or ad accounts: {e}")
        except ValueError as e:
            logging.error(f"Error processing JSON response: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while obtaining user profile: {e}")

        return user_profile

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
    
