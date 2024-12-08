from pydantic import BaseModel, validator
from typing import Optional, List, Union
from datetime import date


# Modelos para FAQ
class FAQBase(BaseModel):
    question: str
    answer: str


class FAQSchema(FAQBase):
    id: int

    class Config:
        from_attributes = True


class FAQCreate(FAQBase):
    pass


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None


class FAQResponse(FAQBase):
    id: int

    class Config:
        from_attributes = True


# Modelos para Ordenes
class OrderBase(BaseModel):
    phone: str
    email: str
    address: str



class Order(OrderBase):
    id: int
    product: str
    cantidad_cajas: int

    class Config:
        from_attributes = True


class OrderUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class ProductInput(BaseModel):
    producto: str
    cantidad: int
    precio: int

class OrderCreate(BaseModel):
    phone: str
    email: Optional[str] = "N/A"
    address: Optional[str] = "N/A"
    ciudad: Optional[str] = "N/A"
    producto: Union[str, List[ProductInput]] 
    cantidad_cajas: Optional[Union[int, str]] = "1"
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    ad_id: Optional[str] = None
    delivery_date: Optional[date] = None

    @validator("cantidad_cajas", pre=True, always=True)
    def convert_cantidad_cajas(cls, v):
        return str(v)


class OrderResponse(BaseModel):
    id: int
    phone: str
    email: Optional[str]
    address: Optional[str]
    ciudad: Optional[str]
    producto: Union[str, List[ProductInput]] 
    cantidad_cajas: Optional[Union[int, str]] = "1"
    nombre: Optional[str]
    apellido: Optional[str]
    ad_id: Optional[str]
    delivery_date: Optional[date]

    class Config:
        from_attributes = True

# Modelos para Cuenta
class Cuenta(BaseModel):
    id: int
    nombre: str
    page_id: str  

    class Config:
        from_attributes = True


class CuentaCreate(BaseModel):
    nombre: str
    page_id: str  



class CuentaUpdate(BaseModel):
    nombre: Optional[str] = None
    page_id: Optional[str] = None  


# Modelos para Productos
class ProductoData(BaseModel):
    nombre: str
    precio: float


class ProductosCreate(BaseModel):
    productos: List[ProductoData]


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    precio: Optional[float] = None


class Producto(BaseModel):
    id: int
    nombre: str
    precio: float

    class Config:
        from_attributes = True


class CuentaProducto(BaseModel):
    id: int
    cuenta_id: int
    producto_id: int
    precio: float

    class Config:
        from_attributes = True


class ProductoCuentaData(BaseModel):
    nombre: str
    precio: float


class ProductosCuentaCreate(BaseModel):
    productos: List[ProductoCuentaData]


class ProductoCuentaResponse(BaseModel):
    id: int
    producto: str
    precio: float

    class Config:
        from_attributes = True

class CiudadCreate(BaseModel):
    nombre: str


class ProductoCiudadCreate(BaseModel):
    productos: List[str]


class CiudadResponse(CiudadCreate):
    id: int
    productos: List[str]

    class Config:
        from_attributes = True

class APIKeyCreate(BaseModel):
    name: str
    key: str