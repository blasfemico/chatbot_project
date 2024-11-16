from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    address = Column(String, nullable=False)
class CiudadProducto(Base):
    __tablename__ = 'ciudad_producto'
    id = Column(Integer, primary_key=True)
    ciudad_id = Column(Integer, ForeignKey('ciudades.id'))
    producto_id = Column(Integer, ForeignKey('productos.id'))
    

class Ciudad(Base):
    __tablename__ = 'ciudades'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    productos = relationship("Producto", secondary="ciudad_producto", back_populates="ciudades")
    cuentas = relationship("CuentaCiudad", back_populates="ciudad")  

class Producto(Base):
    __tablename__ = 'productos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    ciudades = relationship("Ciudad", secondary="ciudad_producto", back_populates="productos")

class Cuenta(Base):
    __tablename__ = 'cuentas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    page_id = Column(String, unique=True, nullable=False)  
    productos = relationship("CuentaProducto", back_populates="cuenta")
    ciudades = relationship("CuentaCiudad", back_populates="cuenta")

class CuentaProducto(Base):
    __tablename__ = 'cuenta_producto'
    id = Column(Integer, primary_key=True)
    cuenta_id = Column(Integer, ForeignKey('cuentas.id'))
    producto_id = Column(Integer, ForeignKey('productos.id'))
    precio = Column(Float, nullable=False)
    cuenta = relationship("Cuenta", back_populates="productos")
    producto = relationship("Producto")

class CuentaCiudad(Base):
    __tablename__ = "cuenta_ciudad"
    
    id = Column(Integer, primary_key=True, index=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas.id"))
    ciudad_id = Column(Integer, ForeignKey("ciudades.id"))

    cuenta = relationship("Cuenta", back_populates="ciudades")
    ciudad = relationship("Ciudad", back_populates="cuentas")



class LastProcessedMessage(Base):
    __tablename__ = 'last_processed_messages'
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String, unique=True, nullable=False)  
    last_message_id = Column(String, nullable=False)   