# app/schemas.py
from pydantic import BaseModel
from typing import Optional, List

# Esquema para la tabla FAQ
class FAQBase(BaseModel):
    question: str
    answer: str

class FAQCreate(FAQBase):
    pass

class FAQ(FAQBase):
    id: int

    class Config:
        from_attributes= True

# Esquema para la tabla Order
class OrderBase(BaseModel):
    phone: str
    email: str
    address: str

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: int

    class Config:
        from_attributes = True

# Esquema para la tabla Product
class ProductBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    city_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    city: Optional["City"] = None  # Relación opcional con City

    class Config:
        from_attributes = True

# Esquema para la tabla City
class CityBase(BaseModel):
    name: str

class CityCreate(CityBase):
    pass

class City(CityBase):
    id: int
    products: List[Product] = []  # Relación con múltiples productos

    class Config:
        from_attributes = True
