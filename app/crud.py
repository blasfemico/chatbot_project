# app/crud.py
from sqlalchemy.orm import Session
from app import models, schemas

class CRUDOrder:
    def create_order(self, db: Session, order: schemas.OrderCreate):
        db_order = models.Order(phone=order.phone, email=order.email, address=order.address)
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order

    def get_orders(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(models.Order).offset(skip).limit(limit).all()

class CRUDFaq:
    def store_pdf_content(self, db: Session, content: list[dict]):
        # Almacena el contenido nuevo
        for item in content:
            db_faq = models.FAQ(question=item["question"], answer=item["answer"])
            db.add(db_faq)
        db.commit()

    def get_response(self, db: Session, question: str):
        # Encuentra la respuesta que más se aproxima a la pregunta
        faq = db.query(models.FAQ).filter(models.FAQ.question == question).first()
        if faq:
            return faq.answer
        return None
