from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    email = Column(String, default="N/A")
    address = Column(String, default="N/A")
    producto = Column(JSON, nullable=False)
    ciudad = Column(String, default="N/A") 
    cantidad_cajas = Column(String, default="1")
    ad_id = Column(String, nullable=True)
    nombre = Column(String, default="N/A")  
    apellido = Column(String, default="N/A")  

class Ciudad(Base):
    __tablename__ = "ciudades"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    phone_prefix = Column(String, unique=True, nullable=True)  
    
    productos = relationship("ProductoCiudad", back_populates="ciudad")


class ProductoCiudad(Base):
    __tablename__ = "producto_ciudad"
    id = Column(Integer, primary_key=True)
    ciudad_id = Column(
        Integer, ForeignKey("ciudades.id", ondelete="CASCADE"), nullable=False
    )
    producto_id = Column(
        Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False
    )

    ciudad = relationship("Ciudad", back_populates="productos")
    producto = relationship("Producto", back_populates="ciudades")


class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)

    ciudades = relationship("ProductoCiudad", back_populates="producto")


class Cuenta(Base):
    __tablename__ = "cuentas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    page_id = Column(String, unique=True, nullable=False)
    productos = relationship("CuentaProducto", back_populates="cuenta")

class CuentaProducto(Base):
    __tablename__ = "cuenta_producto"
    id = Column(Integer, primary_key=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    precio = Column(Float, nullable=False)
    cuenta = relationship("Cuenta", back_populates="productos")
    producto = relationship("Producto")


class LastProcessedMessage(Base):
    __tablename__ = "last_processed_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String, index=True, nullable=False)
    last_message_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_text = Column(String)
    intent = Column(String, default=None) 
    producto = Column(String, nullable=True) 
