# app/schemas.py
from pydantic import BaseModel
from typing import Optional

class AccountBase(BaseModel):
    api_key: str
    name: Optional[str] = None

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    phone: str
    email: str
    address: str

class OrderCreate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: int

    class Config:
        from_attributes = True
