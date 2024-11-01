# app/crud.py
from sqlalchemy.orm import Session
from app import models, schemas

# Clase CRUD para FAQs
class CRUDFaq:
    def create_faq(self, db: Session, faq: schemas.FAQCreate):
        db_faq = models.FAQ(question=faq.question, answer=faq.answer)
        db.add(db_faq)
        db.commit()
        db.refresh(db_faq)
        return db_faq

    def get_faq_by_id(self, db: Session, faq_id: int):
        return db.query(models.FAQ).filter(models.FAQ.id == faq_id).first()

    def get_all_faqs(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(models.FAQ).offset(skip).limit(limit).all()

    # Método para almacenar el contenido del PDF como preguntas y respuestas
    def store_pdf_content(self, db: Session, content: list[dict]):
        # Limpia la tabla de FAQs antes de agregar nuevos registros (opcional)
        db.query(models.FAQ).delete()
        db.commit()
        
        # Guarda las nuevas preguntas y respuestas
        for item in content:
            db_faq = models.FAQ(question=item["question"], answer=item["answer"])
            db.add(db_faq)
        db.commit()
        
    def get_response(self, db: Session, question: str):
        faq = db.query(models.FAQ).filter(models.FAQ.question == question).first()
        if faq:
            return faq.answer
        return "Lo siento, no tengo una respuesta para esa pregunta."

# Clase CRUD para Orders
class CRUDOrder:
    def create_order(self, db: Session, order: schemas.OrderCreate):
        db_order = models.Order(phone=order.phone, email=order.email, address=order.address)
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order

    def get_order_by_id(self, db: Session, order_id: int):
        return db.query(models.Order).filter(models.Order.id == order_id).first()

    def get_all_orders(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(models.Order).offset(skip).limit(limit).all()


# Clase CRUD para Products
class CRUDProduct:
    def create_product(self, db: Session, product: schemas.ProductCreate):
        db_product = models.Product(
            name=product.name,
            price=product.price,
            description=product.description,
            city_id=product.city_id
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

    def get_product_by_id(self, db: Session, product_id: int):
        return db.query(models.Product).filter(models.Product.id == product_id).first()

    def get_all_products(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(models.Product).offset(skip).limit(limit).all()

    def update_product(self, db: Session, product_id: int, product: schemas.ProductCreate):
        db_product = self.get_product_by_id(db, product_id)
        if db_product:
            db_product.name = product.name
            db_product.price = product.price
            db_product.description = product.description
            db_product.city_id = product.city_id
            db.commit()
            db.refresh(db_product)
        return db_product

    def delete_product(self, db: Session, product_id: int):
        db_product = self.get_product_by_id(db, product_id)
        if db_product:
            db.delete(db_product)
            db.commit()
        return db_product


# Clase CRUD para Cities
class CRUDCity:
    def create_city(self, db: Session, city: schemas.CityCreate):
        db_city = models.City(name=city.name)
        db.add(db_city)
        db.commit()
        db.refresh(db_city)
        return db_city

    def get_city_by_id(self, db: Session, city_id: int):
        return db.query(models.City).filter(models.City.id == city_id).first()

    def get_all_cities(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(models.City).offset(skip).limit(limit).all()
