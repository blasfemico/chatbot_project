import re
from typing import Optional
import logging
from stanza import Pipeline
from sentence_transformers import SentenceTransformer, util

class AddressDetection:
    nlp = Pipeline(lang='es', processors='tokenize,ner', quiet=True)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Frases conocidas de direcciones para similitud semántica (deberia actualizarse con nuevos ejemplos mas adelante)
    known_address_phrases = [
        "calle 123 colonia centro",
        "avenida revolución número 45",
        "manzana 4 lote 5 sector B",
        "calle principal número 56 colonia las flores",
    ]
    address_embeddings = model.encode(known_address_phrases, convert_to_tensor=True)

    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Preprocesa el texto eliminando caracteres irrelevantes y normalizando palabras clave.
        """
        replacements = {
            r'\bav\b': 'avenida',
            r'\bmza\b': 'manzana',
            r'\bfracc\b': 'fraccionamiento',
            r'\burb\b': 'urbanización',
            r'\bnum\b': 'número',
            r'\bnro\b': 'número'
        }
        text = text.lower()
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        text = re.sub(r'[^a-zA-Z0-9áéíóúñ#\s]', '', text)  
        return text.strip()

    @staticmethod
    def detect_address_with_similarity(text: str) -> Optional[str]:
        """
        Detecta direcciones usando similitud semántica con embeddings preentrenados.
        """
        preprocessed_text = AddressDetection.preprocess_text(text)
        text_embedding = AddressDetection.model.encode(preprocessed_text, convert_to_tensor=True)
        similarities = util.cos_sim(text_embedding, AddressDetection.address_embeddings)
        max_similarity = similarities.max().item()

        if max_similarity > 0.8:
            logging.info(f"Dirección detectada con similitud semántica: {preprocessed_text}")
            return preprocessed_text
        return None

    @staticmethod
    def detect_address_parts(text: str) -> dict:
        """
        Detecta las partes de una dirección utilizando NLP y separa nombre, teléfono, dirección, ciudad y estado.
        """
        result = {
            "nombre": None,
            "telefono": None,
            "direccion": None,
            "ciudad": None,
            "estado": None,
        }

        try:
            doc = AddressDetection.nlp(text)

    
            tokens = []
            for sentence in doc.sentences:
                tokens.extend(sentence.tokens)
            phone_match = re.search(r'\b\d{10}\b', text)
            if phone_match:
                result["telefono"] = phone_match.group(0)
                text = text.replace(result["telefono"], "")

            name_match = re.match(r'^[A-Za-záéíóúñ\s]+', text)
            if name_match:
                result["nombre"] = name_match.group(0).strip()
                text = text.replace(result["nombre"], "")
            ciudades_estados = [
                "León", "Tijuana", "Monterrey", "Juárez", "Chihuahua",
                "Baja California", "Nuevo León", "Nayarit", "Querétaro", "Morelia"
            ]
            for loc in ciudades_estados:
                if loc.lower() in text.lower():
                    if result["ciudad"] is None:
                        result["ciudad"] = loc
                    else:
                        result["estado"] = loc
                    text = text.replace(loc, "")

            patterns = [
                r'\b(?:calle|avenida|av|manzana|circuito|sector|colonia)\s*\w+.*',
                r'\b\w+[\s\w]+\#\d+',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["direccion"] = match.group(0).strip()
                    break

            if not result["direccion"]:
                for word in tokens:
                    if any(keyword in word.text.lower() for keyword in ["calle", "avenida", "colonia", "manzana"]):
                        if result["direccion"]:
                            result["direccion"] += f" {word.text}"
                        else:
                            result["direccion"] = word.text

        except Exception as e:
            logging.error(f"Error al detectar partes de dirección: {e}")

        return result
