# app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas

class CRUDAccount:
    def __init__(self, model):
        self.model = model

    def create_account(self, db: Session, account: schemas.AccountCreate):
        db_account = self.model(api_key=account.api_key, name=account.name)
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        return db_account

    def get_account(self, db: Session, account_id: int):
        return db.query(self.model).filter(self.model.id == account_id).first()

class CRUDOrder:
    def __init__(self, model):
        self.model = model

    def create_order(self, db: Session, order: schemas.OrderCreate):
        db_order = self.model(phone=order.phone, email=order.email, address=order.address)
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order

    def get_orders(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(self.model).offset(skip).limit(limit).all()
