from pydantic import BaseModel
from typing import Optional, List


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


class OrderCreate(BaseModel):
    phone: str
    email: Optional[str] = "N/A"
    address: Optional[str] = "N/A"
    producto: str
    cantidad_cajas: Optional[int] = 1
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    ad_id: Optional[str] = None 

class OrderResponse(BaseModel):
    id: int
    phone: str
    email: str
    address: str
    producto: str
    cantidad_cajas: int
    nombre: str
    apellido: str

    class Config:
        from_attributes = True


# Modelos para Cuenta
class Cuenta(BaseModel):
    id: int
    nombre: str
    page_id: str  # Cambiado a page_id en lugar de api_key

    class Config:
        from_attributes = True


class CuentaCreate(BaseModel):
    nombre: str
    page_id: str  # Definimos page_id como campo requerido al crear una cuenta


class CuentaUpdate(BaseModel):
    nombre: Optional[str] = None
    page_id: Optional[str] = None  # Permitir actualizar page_id si es necesario


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
    producto: str
    precio: float


class CiudadCreate(BaseModel):
    nombre: str


class ProductoCiudadCreate(BaseModel):
    productos: List[str]


class CiudadResponse(CiudadCreate):
    id: int
    productos: List[str]

    class Config:
        from_attributes = True