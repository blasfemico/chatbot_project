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
        from_attributes = True

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



# Esquema para crear una nueva cuenta
class CuentaCreate(BaseModel):
    nombre: str
    api_key: str

class Cuenta(BaseModel):
    id: int
    nombre: str
    api_key: str
    # Eliminamos la relación directa con `productos` para evitar recursión
    class Config:
        from_attribute = True

# Esquema para crear un nuevo producto
class ProductoCreate(BaseModel):
    nombre: str

class Producto(BaseModel):
    id: int
    nombre: str
    # Eliminamos la relación directa con `cuentas` para evitar recursión
    class Config:
        orm_mode = True

# Esquema para la relación entre cuentas y productos, incluyendo el precio específico
class CuentaProducto(BaseModel):
    id: int
    cuenta_id: int
    producto_id: int
    precio: float
    # Evitamos la inclusión de cuenta y producto completos aquí para romper la recursión
    class Config:
        from_attribute = True