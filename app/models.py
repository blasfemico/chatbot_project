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
    pdf_id = Column(Integer, ForeignKey("pdfs.id"))  
    pdf = relationship("PDF", back_populates="faqs")  

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product = relationship("Product")  # Relación con el producto
    total_price = Column(Float, nullable=False)
    status = Column(String, default="pending")  # Estado de la orden

class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    products = relationship("Product", back_populates="city", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    city = relationship("City", back_populates="products")
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class FacebookAccount(Base):
    __tablename__ = "facebook_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_name = Column(String, unique=True, nullable=False)
    api_key = Column(String, nullable=False)

