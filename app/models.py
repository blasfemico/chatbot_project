from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

# Tabla para almacenar PDFs y FAQs asociados
class PDF(Base):
    __tablename__ = "pdfs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Nombre del PDF
    faqs = relationship("FAQ", back_populates="pdf")  # Relación con FAQ

class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    pdf_id = Column(Integer, ForeignKey("pdfs.id"))  # Definir ForeignKey correctamente
    pdf = relationship("PDF", back_populates="faqs")  # Relación inversa


# Tabla para almacenar pedidos
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    address = Column(String, nullable=False)

# Tabla para almacenar productos generales
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String)
    city_id = Column(Integer, ForeignKey("cities.id"))

    # Relación con City para soportar especificaciones por ciudad
    city = relationship("City", back_populates="products")

# Tabla para almacenar ciudades
class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    products = relationship("Product", back_populates="city")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Modelo para almacenar cuentas de Facebook con API Keys
class FacebookAccount(Base):
    __tablename__ = "facebook_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_name = Column(String, unique=True, nullable=False)
    api_key = Column(String, nullable=False)

# Nuevos modelos para gestionar cuentas y productos con precios personalizados

# Tabla para almacenar cuentas generales
class Cuenta(Base):
    __tablename__ = 'cuentas'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    productos = relationship("CuentaProducto", back_populates="cuenta")

# Tabla para productos específicos de cuentas con precios personalizados
class Producto(Base):
    __tablename__ = 'productos'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    cuenta_productos = relationship("CuentaProducto", back_populates="producto")

# Tabla intermedia que relaciona cuentas y productos, permitiendo precios específicos por cuenta
class CuentaProducto(Base):
    __tablename__ = 'cuenta_producto'
    
    id = Column(Integer, primary_key=True)
    cuenta_id = Column(Integer, ForeignKey('cuentas.id'))
    producto_id = Column(Integer, ForeignKey('productos.id'))
    precio = Column(Float, nullable=False)
    
    cuenta = relationship("Cuenta", back_populates="productos")
    producto = relationship("Producto", back_populates="cuenta_productos")
