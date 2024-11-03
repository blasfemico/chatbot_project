
from pydantic import BaseModel
from typing import Optional, List


class FAQBase(BaseModel):
    question: str
    answer: str

class FAQCreate(FAQBase):
    pass

class FAQ(FAQBase):
    id: int

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    phone: str
    email: str
    address: str

class OrderCreate(BaseModel):
    phone: str
    address: str = None
    customer_name: str = None
    product_id: int
    total_price: float

class Order(OrderBase):
    id: int

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    city_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    city: Optional["City"] = None  

    class Config:
        from_attributes = True


class CityBase(BaseModel):
    name: str

class CityCreate(CityBase):
    pass

class City(CityBase):
    id: int
    products: List[Product] = []  

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    phone: str
    address: str = None
    content: str  # El mensaje del cliente en el chat
    customer_name: str = None