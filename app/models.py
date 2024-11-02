# app/models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

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

# Tabla para almacenar productos
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

