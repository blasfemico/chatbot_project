from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from app.models import (
    FAQ,
    Cuenta,
    CuentaProducto,
    Order,
    Producto,
    Ciudad,
    ProductoCiudad,
)
from app.schemas import (
    FAQCreate,
    FAQUpdate,
    CuentaCreate,
    CuentaUpdate,
    ProductosCreate,
    CiudadCreate,
    ProductosCuentaCreate,
)
from datetime import datetime
from app import schemas
import json
from sentence_transformers import SentenceTransformer
import logging
from typing import List
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logging.basicConfig(level=logging.INFO)


model = SentenceTransformer("all-MiniLM-L6-v2")


class CRUDFaq:
    def __init__(self, model):
        self.model = model

    def create_faq(self, db: Session, faq_data: FAQCreate):
        embedding = self.generate_embedding(faq_data.question)
        db_faq = FAQ(
            question=faq_data.question,
            answer=faq_data.answer,
            embedding=json.dumps(embedding),
        )
        db.add(db_faq)
        db.commit()
        db.refresh(db_faq)
        return db_faq

    def update_faq(self, db: Session, faq_id: int, faq_data: FAQUpdate):
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if faq:
            if faq_data.question:
                faq.question = faq_data.question
                faq.embedding = json.dumps(self.generate_embedding(faq_data.question))
            if faq_data.answer:
                faq.answer = faq_data.answer
            db.commit()
            db.refresh(faq)
        return faq

    def delete_faq(self, db: Session, faq_id: int):
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if faq:
            db.delete(faq)
            db.commit()

    def generate_embedding(self, text: str):
        return self.model.encode(text).tolist()

    def find_exact_faq(self, db: Session, question: str):
        return db.query(FAQ).filter(FAQ.question == question).first()

    def get_all_faqs(self, db: Session):
        return db.query(FAQ).all()


class CRUDProduct:
    def create_producto(self, db: Session, producto_data: ProductosCreate):
        """Crea un nuevo producto."""
        db_producto = Producto(nombre=producto_data.nombre)
        db.add(db_producto)
        db.commit()
        db.refresh(db_producto)
        return db_producto

    def get_productos_by_cuenta(self, db: Session, cuenta_id: int):
        """Obtiene todos los productos y precios asociados a una cuenta específica."""
        productos = (
            db.query(CuentaProducto)
            .join(Producto)
            .filter(CuentaProducto.cuenta_id == cuenta_id)
            .all()
        )
        return [{"producto": p.producto.nombre, "precio": p.precio} for p in productos]

    def get_all_productos(self, db: Session):
        """Obtiene todos los productos en la base de datos."""
        return db.query(Producto).all()


class CRUDCuentaProducto:
    def add_products_to_account(
        self, db: Session, cuenta_id: int, productos_data: ProductosCuentaCreate
    ):
        created_productos = []

        for producto_data in productos_data.productos:
            nuevo_producto = Producto(nombre=producto_data.nombre)
            db.add(nuevo_producto)
            db.commit()
            db.refresh(nuevo_producto)

            cuenta_producto = CuentaProducto(
                cuenta_id=cuenta_id,
                producto_id=nuevo_producto.id,
                precio=producto_data.precio,
            )
            db.add(cuenta_producto)
            created_productos.append(cuenta_producto)

        db.commit()

        return {
            "message": "Productos creados y asociados a la cuenta",
            "productos": [
                {
                    "producto_id": p.producto_id,
                    "cuenta_id": p.cuenta_id,
                    "precio": p.precio,
                }
                for p in created_productos
            ],
        }

    def update_product_price_for_account(
        self, db: Session, cuenta_id: int, producto_id: int, new_price: float
    ):
        """Actualiza el precio de un producto para una cuenta específica."""
        cuenta_producto = (
            db.query(CuentaProducto)
            .filter_by(cuenta_id=cuenta_id, producto_id=producto_id)
            .first()
        )
        if cuenta_producto:
            cuenta_producto.precio = new_price
            db.commit()
            db.refresh(cuenta_producto)
        return cuenta_producto

    def remove_product_from_account(
        self, db: Session, cuenta_id: int, producto_id: int
    ):
        """Elimina la relación de un producto con una cuenta."""
        cuenta_producto = (
            db.query(CuentaProducto)
            .filter_by(cuenta_id=cuenta_id, producto_id=producto_id)
            .first()
        )
        if cuenta_producto:
            db.delete(cuenta_producto)
            db.commit()
            return True
        return False

    def get_products_for_account(self, db: Session, cuenta_id: int):
        """Obtiene la lista de productos y precios de una cuenta específica."""
        productos = (
            db.query(
                Producto.id.label("id"), 
                Producto.nombre.label("producto"), 
                CuentaProducto.precio.label("precio")
            )
            .join(CuentaProducto, Producto.id == CuentaProducto.producto_id)
            .filter(CuentaProducto.cuenta_id == cuenta_id)
            .all()
        )

        if not productos:
            raise HTTPException(status_code=404, detail="No se encontraron productos para esta cuenta.")
        
        # Devuelve una lista de diccionarios con id, producto y precio
        return [{"id": p.id, "producto": p.producto, "precio": p.precio} for p in productos]

class CRUDOrder:
    @staticmethod
    def get_delivery_day_message():
        today = datetime.today().weekday() 
        delivery_day = "lunes" if today == 5 else "mañana"
        return f"Su pedido se entregará el {delivery_day}."

    def create_order(self, db: Session, order: schemas.OrderCreate, nombre: str, apellido: str) -> schemas.OrderResponse:
        try:
            if not order.phone:
                raise HTTPException(status_code=400, detail="El campo 'phone' es obligatorio.")
            if not order.producto:
                raise HTTPException(status_code=400, detail="El campo 'producto' es obligatorio.")

            logging.info(f"Creando nueva orden con datos: phone={order.phone}, email={order.email}, address={order.address}, "
                        f"producto={order.producto}, cantidad_cajas={order.cantidad_cajas}, nombre={nombre}, apellido={apellido}")

            new_order = Order(
                phone=order.phone,
                email=order.email or "N/A",
                address=order.address or "N/A",
                producto=order.producto,
                cantidad_cajas=order.cantidad_cajas or 1,
                nombre=nombre,
                apellido=apellido,
                ad_id=order.ad_id or "N/A"
            )
            db.add(new_order)
            db.commit()
            db.refresh(new_order)
            return schemas.OrderResponse.from_orm(new_order)
        except IntegrityError as e:
            db.rollback()
            logging.error(f"Error de integridad al crear la orden: {str(e)}")
            raise HTTPException(status_code=400, detail="Error de integridad en la base de datos.")
        except SQLAlchemyError as e:
            db.rollback()
            logging.error(f"Error general de SQLAlchemy al crear la orden: {str(e)}")
            raise HTTPException(status_code=500, detail="Error en la base de datos.")
        except Exception as e:
            db.rollback()
            logging.error(f"Error inesperado al crear la orden: {str(e)}")
            raise HTTPException(status_code=500, detail="Error inesperado al crear la orden.")



    def update_order(self, db: Session, order_id: int, order_data: schemas.OrderUpdate):
        try:
            logging.info(f"Actualizando la orden con ID {order_id}.")
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                if order_data.phone:
                    order.phone = order_data.phone
                if order_data.email:
                    order.email = order_data.email
                if order_data.address:
                    order.address = order_data.address
                db.commit()
                db.refresh(order)
                logging.info(f"Orden actualizada exitosamente: ID {order.id}")
                return order
            else:
                logging.warning(f"No se encontró la orden con ID {order_id}.")
                raise HTTPException(status_code=404, detail="Orden no encontrada")
        except Exception as e:
            logging.error(f"Error al actualizar la orden: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Error al actualizar la orden.")

    def delete_order(self, db: Session, order_id: int):
        try:
            logging.info(f"Eliminando la orden con ID {order_id}.")
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                db.delete(order)
                db.commit()
                logging.info(f"Orden eliminada exitosamente: ID {order_id}")
                return True
            else:
                logging.warning(f"No se encontró la orden con ID {order_id} para eliminar.")
                raise HTTPException(status_code=404, detail="Orden no encontrada")
        except Exception as e:
            logging.error(f"Error al eliminar la orden: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Error al eliminar la orden.")

    def get_order_by_id(self, db: Session, order_id: int):
        logging.info(f"Obteniendo la orden con ID {order_id}.")
        return db.query(Order).filter(Order.id == order_id).first()

    def get_all_orders(self, db: Session, skip: int = 0, limit: int = 10):
        logging.info(f"Obteniendo todas las órdenes. Saltar: {skip}, Límite: {limit}")
        orders_query = db.execute(
            select(
                Order.id,
                Order.phone,
                Order.email,
                Order.address,
                Order.producto,
                Order.cantidad_cajas,
                Order.nombre,   
                Order.apellido,  
                Order.ad_id

                
            ).offset(skip).limit(limit)
        )
        orders = orders_query.fetchall()
        

        return [
            {
                "id": order.id,
                "phone": order.phone or "N/A",
                "email": order.email or "N/A",
                "address": order.address or "N/A",
                "producto": order.producto,
                "cantidad_cajas": order.cantidad_cajas,
                "nombre": order.nombre or "N/A",   
                "apellido": order.apellido or "N/A",
                "ad_id": order.ad_id or "N/A"
            }
            for order in orders
        ]



class CRUDCuenta:
    def create_cuenta(self, db: Session, cuenta_data: CuentaCreate):
        db_cuenta = Cuenta(nombre=cuenta_data.nombre, page_id=cuenta_data.page_id)
        db.add(db_cuenta)
        db.commit()
        db.refresh(db_cuenta)
        return db_cuenta

    def update_cuenta(self, db: Session, cuenta_id: int, cuenta_data: CuentaUpdate):
        cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
        if cuenta:
            if cuenta_data.nombre:
                cuenta.nombre = cuenta_data.nombre
            if cuenta_data.api_key:
                cuenta.api_key = cuenta_data.api_key
            db.commit()
            db.refresh(cuenta)
        return cuenta

    def delete_cuenta(self, db: Session, cuenta_id: int):
        cuenta = db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
        if cuenta:
            db.delete(cuenta)
            db.commit()
        return cuenta

    def get_cuenta_by_id(self, db: Session, cuenta_id: int):
        return db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()

    def get_all_cuentas(self, db: Session, skip: int = 0, limit: int = 10):
        return db.query(Cuenta).offset(skip).limit(limit).all()


class CRUDCiudad:
    def create_ciudad(self, db: Session, ciudad_data: CiudadCreate):
        db_ciudad = Ciudad(nombre=ciudad_data.nombre)
        db.add(db_ciudad)
        db.commit()
        db.refresh(db_ciudad)
        return db_ciudad

    @staticmethod
    def get_city_by_phone_prefix(db: Session, prefix: str) -> str:
        """
        Obtiene la ciudad basada en el prefijo del teléfono.
        """
        ciudad = db.query(Ciudad).filter(Ciudad.phone_prefix == prefix).first()
        return ciudad.nombre if ciudad else None


    def add_products_to_city(
        self, db: Session, ciudad_id: int, productos_nombres: List[str]
    ):
        ciudad = db.query(Ciudad).filter(Ciudad.id == ciudad_id).first()
        if not ciudad:
            raise HTTPException(status_code=404, detail="Ciudad no encontrada")

        for nombre_producto in productos_nombres:
            producto = (
                db.query(Producto).filter(Producto.nombre == nombre_producto).first()
            )
            if not producto:
                producto = Producto(nombre=nombre_producto)
                db.add(producto)
                db.commit()
                db.refresh(producto)

            producto_ciudad = ProductoCiudad(
                ciudad_id=ciudad.id, producto_id=producto.id
            )
            db.add(producto_ciudad)
        db.commit()
        return {"message": "Productos asociados a la ciudad"}

    def get_products_for_city(self, db: Session, ciudad_id: int):
        productos = (
            db.query(Producto.nombre)
            .join(ProductoCiudad, Producto.id == ProductoCiudad.producto_id)
            .filter(ProductoCiudad.ciudad_id == ciudad_id)
            .all()
        )
        return [{"nombre": p[0]} for p in productos]
    
    def delete_product_from_city(self, db: Session, ciudad_id: int, producto_id: int):
        """
        Elimina un producto específico de una ciudad.
        """
        producto_ciudad = (
            db.query(ProductoCiudad)
            .filter(ProductoCiudad.ciudad_id == ciudad_id, ProductoCiudad.producto_id == producto_id)
            .first()
        )
        if producto_ciudad:
            db.delete(producto_ciudad)
            db.commit()
            return True
        return False
    
    def delete_all_products_from_city(self, db: Session, ciudad_id: int):
        """
        Elimina todos los productos asociados a una ciudad.
        """
        productos_ciudad = db.query(ProductoCiudad).filter(ProductoCiudad.ciudad_id == ciudad_id)
        if productos_ciudad.count() > 0:
            productos_ciudad.delete(synchronize_session=False)
            db.commit()
        return True



    @staticmethod
    def get_all_cities(db: Session):
        return db.query(Ciudad).all()
    
    @staticmethod
    def delete_ciudad(self, db: Session, ciudad_id: int):
        ciudad = db.query(Ciudad).filter(Ciudad.id == ciudad_id).first()
        if not ciudad:
            raise HTTPException(status_code=404, detail="Ciudad no encontrada")
        db.query(ProductoCiudad).filter(ProductoCiudad.ciudad_id == ciudad_id).delete()
        db.delete(ciudad)
        db.commit()
        return {"message": f"Ciudad con ID {ciudad_id} eliminada exitosamente"}
