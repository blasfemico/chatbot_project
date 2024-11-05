from sqlalchemy.orm import Session
from app import models, schemas
from typing import List, Dict

# CRUD para FAQs
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

    def create_pdf_with_faqs(self, db: Session, content: List[Dict[str, str]], pdf_name: str):
        pdf_record = models.PDF(name=pdf_name)
        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)
        
        for item in content:
            question = item.get("question")
            answer = item.get("answer")
            faq_entry = models.FAQ(question=question, answer=answer, pdf_id=pdf_record.id)
            db.add(faq_entry)
        
        db.commit()

    def get_response(self, db: Session, question: str):
        faq = db.query(models.FAQ).filter(models.FAQ.question == question).first()
        if faq:
            return faq.answer
        return "Lo siento, no tengo una respuesta para esa pregunta."

# CRUD para Ordenes
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

# CRUD para Cuentas
class CRUDCuenta:
    def create_cuenta(self, db: Session, cuenta: schemas.CuentaCreate):
        db_cuenta = models.Cuenta(nombre=cuenta.nombre, api_key=cuenta.api_key)
        db.add(db_cuenta)
        db.commit()
        db.refresh(db_cuenta)
        return db_cuenta

    def get_all_cuentas(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(models.Cuenta).offset(skip).limit(limit).all()

    def get_cuenta_by_id(self, db: Session, cuenta_id: int):
        return db.query(models.Cuenta).filter(models.Cuenta.id == cuenta_id).first()

# CRUD para Productos
class CRUDProducto:
    def create_producto(self, db: Session, producto: schemas.ProductoCreate):
        db_producto = models.Producto(nombre=producto.nombre)
        db.add(db_producto)
        db.commit()
        db.refresh(db_producto)
        return db_producto

    def get_producto_by_nombre(self, db: Session, nombre: str):
        return db.query(models.Producto).filter(models.Producto.nombre == nombre).first()

# CRUD para la relación entre Cuenta y Producto
class CRUDCuentaProducto:
    def add_producto_to_cuenta(self, db: Session, cuenta_id: int, producto: schemas.ProductoCreate, precio: float):
        # Verificar si el producto ya existe o crearlo
        db_producto = db.query(models.Producto).filter(models.Producto.nombre == producto.nombre).first()
        if not db_producto:
            db_producto = models.Producto(nombre=producto.nombre)
            db.add(db_producto)
            db.commit()
            db.refresh(db_producto)
        
        # Asociar el producto con la cuenta
        db_cuenta_producto = models.CuentaProducto(cuenta_id=cuenta_id, producto_id=db_producto.id, precio=precio)
        db.add(db_cuenta_producto)
        db.commit()
        db.refresh(db_cuenta_producto)
        return db_cuenta_producto

    def get_productos_by_cuenta(self, db: Session, cuenta_id: int):
        return db.query(models.CuentaProducto).filter(models.CuentaProducto.cuenta_id == cuenta_id).all()

# CRUD para Mensajes
class CRUDMessage:
    def create_message(self, db: Session, user_id: int, content: str):
        message = models.Message(user_id=user_id, content=content)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def get_messages(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(models.Message).order_by(models.Message.timestamp.desc()).offset(skip).limit(limit).all()

# CRUD para Cuentas de Facebook
class CRUDFacebookAccount:
    def add_facebook_account(self, db: Session, account_name: str, api_key: str):
        account = models.FacebookAccount(account_name=account_name, api_key=api_key)
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def get_facebook_account(self, db: Session, account_name: str):
        return db.query(models.FacebookAccount).filter(models.FacebookAccount.account_name == account_name).first()

    def update_facebook_account(self, db: Session, account_name: str, api_key: str):
        account = self.get_facebook_account(db, account_name)
        if account:
            account.api_key = api_key
            db.commit()
            db.refresh(account)
        return account
