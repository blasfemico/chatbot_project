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
from app.schemas import ProductInput
from typing import List
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
        

        return [{"id": p.id, "producto": p.producto, "precio": p.precio} for p in productos]

class CRUDOrder:
    @staticmethod
    def get_delivery_day_message():
        today = datetime.today().weekday()
        delivery_day = "lunes" if today == 5 else "mañana"
        return f"Su pedido se entregará el {delivery_day}."
    
    @staticmethod
    def serialize_products(productos: list[ProductInput]) -> str:
        """Convierte una lista de ProductInput a JSON."""
        try:
            return json.dumps([p.dict() for p in productos])
        except Exception as e:
            raise ValueError(f"Error al serializar productos: {e}")

    @staticmethod
    def deserialize_products(productos_str: str) -> list[dict]:
        """Convierte un JSON de productos a una lista de diccionarios."""
        try:
            return json.loads(productos_str)
        except Exception as e:
            raise ValueError(f"Error al deserializar productos: {e}")

    def create_order(self, db: Session, order: schemas.OrderCreate, nombre: str, apellido: str):
        """Crea una nueva orden en la base de datos."""
        try:
            if isinstance(order.producto, list):
                order.producto = [
                    p.dict() if hasattr(p, "dict") else p
                    for p in order.producto
                ]
            elif isinstance(order.producto, str):
                try:
                    order.producto = json.loads(order.producto)
                except json.JSONDecodeError:
                    raise ValueError("El campo 'producto' debe ser una lista válida o una cadena JSON correcta.")

            new_order = Order(
                phone=order.phone,
                email=order.email or "N/A",
                address=order.address or "N/A",
                producto=json.dumps(order.producto),
                ciudad=order.ciudad or "N/A",
                cantidad_cajas=", ".join(
                    [str(p["cantidad"]) for p in order.producto]
                ),
                nombre=nombre,
                apellido=apellido,
                ad_id=order.ad_id or "N/A",
                delivery_date=order.delivery_date,
            )
            db.add(new_order)
            db.commit()
            db.refresh(new_order)

            return schemas.OrderResponse.from_orm(new_order)
        except Exception as e:
            db.rollback()
            logging.error(f"Error al crear la orden: {e}")
            raise HTTPException(status_code=500, detail="Error al crear la orden.")

    def delete_order(self, db: Session, order_id: int):
        """Elimina una orden por su ID."""
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
        """Obtiene una orden por su ID."""
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(status_code=404, detail="Orden no encontrada.")

            productos = self.deserialize_products(order.producto)

            return {
                "id": order.id,
                "phone": order.phone or "N/A",
                "email": order.email or "N/A",
                "address": order.address or "N/A",
                "ciudad": order.ciudad or "N/A",
                "producto": productos,  
                "cantidad_cajas": order.cantidad_cajas or "0",
                "nombre": order.nombre or "N/A",
                "apellido": order.apellido or "N/A",
                "ad_id": order.ad_id or "N/A",
                "delivery_date": order.delivery_date or "N/A",
            }
        except Exception as e:
            logging.error(f"Error al obtener la orden con ID {order_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al obtener la orden.")


    def get_all_orders(self, db: Session, skip: int = 0, limit: int = 10):
        """Obtiene todas las órdenes con los productos correctamente deserializados."""
        logging.info(f"Obteniendo todas las órdenes. Saltar: {skip}, Límite: {limit}")
        try:
            orders_query = db.query(Order).offset(skip).limit(limit).all()
            orders = []

            for order in orders_query:
                productos = self.deserialize_products(order.producto)

                orders.append({
                    "id": order.id,
                    "phone": order.phone or "N/A",
                    "email": order.email or "N/A",
                    "address": order.address or "N/A",
                    "ciudad": order.ciudad or "N/A",
                    "producto": productos,  # Lista de diccionarios con `precio`
                    "cantidad_cajas": order.cantidad_cajas or "0",
                    "nombre": order.nombre or "N/A",
                    "apellido": order.apellido or "N/A",
                    "ad_id": order.ad_id or "N/A",
                    "delivery_date": order.delivery_date or "N/A",
                })

            return orders
        except Exception as e:
            logging.error(f"Error al obtener las órdenes: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al obtener las órdenes.")





    def delete_all_orders(self, db: Session) -> dict:
        """Elimina todas las órdenes de la base de datos."""
        try:
            logging.info("Eliminando todas las órdenes.")
            deleted_count = db.query(Order).delete()
            db.commit()
            logging.info(f"Se eliminaron {deleted_count} órdenes.")
            return {"message": f"Se eliminaron {deleted_count} órdenes correctamente."}
        except Exception as e:
            logging.error(f"Error al eliminar todas las órdenes: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Error al eliminar todas las órdenes.")

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
        if not ciudad:
            logging.warning(f"No se encontró ciudad para el prefijo {prefix}.")
            return "N/A"



    def add_products_to_city(
        self, db: Session, ciudad_id: int, productos_nombres: List[str]
    ):
        ciudad = db.query(Ciudad).filter(Ciudad.id == ciudad_id).first()
        if not ciudad:
            raise HTTPException(status_code=404, detail="Ciudad no encontrada")

        productos_asociados = []
        for nombre_producto in productos_nombres:
            producto = db.query(Producto).filter(Producto.nombre == nombre_producto).first()
            if not producto:
                producto = Producto(nombre=nombre_producto)
                db.add(producto)
                db.commit()
                db.refresh(producto)

            producto_ciudad = ProductoCiudad(
                ciudad_id=ciudad.id, producto_id=producto.id
            )
            db.add(producto_ciudad)
            productos_asociados.append({
                "id": producto.id,
                "nombre": producto.nombre
            })
        db.commit()
        return {"message": "Productos asociados a la ciudad", "productos": productos_asociados}


    def get_products_for_city(self, db: Session, ciudad_id: int):
        productos = (
            db.query(Producto.id, Producto.nombre)
            .join(ProductoCiudad, Producto.id == ProductoCiudad.producto_id)
            .filter(ProductoCiudad.ciudad_id == ciudad_id)
            .all()
        )
        return [{"id": p.id, "nombre": p.nombre} for p in productos]

    
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
        try:
            productos_ciudad = db.query(ProductoCiudad).filter(ProductoCiudad.ciudad_id == ciudad_id)
            count = productos_ciudad.count() 
            if count > 0:
                productos_ciudad.delete(synchronize_session=False)
                db.commit()
            return {"deleted_count": count}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def delete_ciudad(self, db: Session, ciudad_id: int):
        ciudad = db.query(Ciudad).filter(Ciudad.id == ciudad_id).first()
        if ciudad:
            db.delete(ciudad)
            db.commit()
        return ciudad

    @staticmethod
    def get_all_cities(db: Session):
        return db.query(Ciudad).all()
    
    