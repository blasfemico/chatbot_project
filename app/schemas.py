# app/schemas.py
from pydantic import BaseModel

class OrderBase(BaseModel):
    phone: str
    email: str
    address: str

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: int

    class Config:
        from_attributes= True
