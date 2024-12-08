from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app import schemas
from app.schemas import ProductInput
from app.crud import CRUDOrder
from app.database import get_db
from typing import List, Dict
import logging
from openpyxl import Workbook
import os
from typing import Optional
from fastapi.responses import FileResponse
import re
import tempfile
import json

router = APIRouter()

class OrderService:
    @staticmethod
    def parse_product_input(input_text: str) -> List[dict]:
        """
        Convierte cadenas como '5 cajas de Acxion y 3 cajas de Redotex' en listas de diccionarios.
        """
        productos = []
        try:
            items = re.split(r"\s*y\s*", input_text.lower())  # Separar por "y"
            for item in items:
                match = re.match(r"(\d+)\s*cajas?\s+de\s+(.+)", item.strip())
                if match:
                    cantidad = int(match.group(1))
                    producto = match.group(2).strip()
                    productos.append({"producto": producto, "cantidad": cantidad})
        except Exception as e:
            raise ValueError(f"Error al procesar la entrada de productos: {e}")
        return productos

    @staticmethod
    def serialize_products(productos: List[ProductInput]) -> str:
        """Convierte una lista de productos a JSON."""
        return json.dumps([p.dict() for p in productos])

    @staticmethod
    def deserialize_products(productos_str: str) -> List[ProductInput]:
        """Convierte un JSON de productos a una lista de ProductInput."""
        try:
            productos = json.loads(productos_str)
            return [ProductInput(**p) for p in productos]
        except Exception as e:
            raise ValueError(f"Error al deserializar productos: {e}")

    @staticmethod
    async def create_order(order_data: schemas.OrderCreate, db: Session, nombre: str = "N/A", apellido: str = "N/A") -> dict:
        try:
            if isinstance(order_data.producto, list):
                order_data.producto = OrderService.serialize_products(order_data.producto)

            crud_order = CRUDOrder()
            new_order = crud_order.create_order(db=db, order=order_data, nombre=nombre, apellido=apellido)
            
            return {
                "message": "Orden creada exitosamente.",
                "order": new_order
            }
        except ValueError as ve:
            logging.error(f"Error de validación en el campo 'producto': {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logging.error(f"Error al crear la orden: {e}")
            raise HTTPException(status_code=500, detail="Error al crear el pedido.")

    @staticmethod
    def get_safe_file_path(directory: str, filename: str = "ordenes_exportadas.xlsx") -> str:
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)
        filename = filename if filename.endswith(".xlsx") else f"{filename}.xlsx"
        file_path = os.path.join(directory, filename)
        
        return file_path
            
    @staticmethod
    async def update_order(order_id: int, order_data: schemas.OrderUpdate, db: Session) -> dict:
        try:
            crud_order = CRUDOrder()
            updated_order = crud_order.update_order(db=db, order_id=order_id, order_data=order_data)
            if not updated_order:
                raise HTTPException(status_code=404, detail="Orden no encontrada")
            return {
                "message": "Orden actualizada correctamente",
                "order": updated_order
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error al actualizar el pedido: {str(e)}")

    @staticmethod
    async def get_orders(skip: int, limit: int, db: Session) -> list[schemas.OrderResponse]:
        try:
            crud_order = CRUDOrder()
            orders = crud_order.get_all_orders(db=db, skip=skip, limit=limit)
            return [schemas.OrderResponse.from_orm(order) for order in orders]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error al obtener los pedidos: {str(e)}")

    @staticmethod
    async def get_order_by_id(order_id: int, db: Session) -> schemas.OrderResponse:
        try:
            crud_order = CRUDOrder()
            order = crud_order.get_order_by_id(db=db, order_id=order_id)
            if order is None:
                raise HTTPException(status_code=404, detail="Pedido no encontrado")
            return schemas.OrderResponse.from_orm(order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error al obtener el pedido: {str(e)}")

    @staticmethod
    async def delete_order(order_id: int, db: Session) -> dict:
        crud_order = CRUDOrder()
        deleted = crud_order.delete_order(db=db, order_id=order_id)
        if deleted:
            return {"message": f"Orden con ID {order_id} eliminada correctamente"}
        else:
            raise HTTPException(status_code=404, detail="Orden no encontrada")

    @staticmethod
    async def export_orders_to_excel(db: Session, file_path: Optional[str] = None) -> str:
        """Exporta las órdenes a un archivo Excel con deserialización de productos."""
        try:
            if not file_path:
                temp_dir = tempfile.mkdtemp()
                file_path = os.path.join(temp_dir, "ordenes_exportadas.xlsx")

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Órdenes"

   
            headers = [
                "Teléfono", "Nombre", "Apellido", "Producto", 
                "Cantidad", "Precio", "Ciudad", "Dirección", "Ad ID"
            ]
            sheet.append(headers)

        
            orders = CRUDOrder().get_all_orders(db)

            for order in orders:

                productos = order["producto"]
                if isinstance(productos, str):
                    try:
                        productos = json.loads(productos)
                    except json.JSONDecodeError:
                        logging.error(f"Error al deserializar productos: {productos}")
                        productos = []
                for producto in productos:
                    row = [
                        order["phone"], 
                        order["nombre"], 
                        order["apellido"],
                        producto.get("producto", "N/A"),
                        producto.get("cantidad", 0),     
                        producto.get("precio", 0.0),   
                        order["ciudad"], 
                        order["address"], 
                        order["ad_id"],
                        order["delivery_date"]
                    ]
                    sheet.append(row)
            workbook.save(file_path)
            os.chmod(file_path, 0o600) 
            return file_path

        except Exception as e:
            logging.error(f"Error exportando órdenes a Excel: {e}")
            raise HTTPException(status_code=500, detail="Error al exportar órdenes.")




@router.post("/orders/", response_model=dict)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    return await OrderService.create_order(order, db)

@router.get("/orders/{order_id}", response_model=schemas.OrderResponse)
async def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    """Obtiene una orden específica por ID."""
    crud_order = CRUDOrder()
    order_data = crud_order.get_order_by_id(db, order_id)
    return schemas.OrderResponse(**order_data)

@router.get("/", response_model=List[schemas.Order])
async def get_orders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return await OrderService.get_orders(skip, limit, db)

@router.delete("/orders/{order_id}", response_model=dict)
async def delete_order(order_id: int, db: Session = Depends(get_db)):
    return await OrderService.delete_order(order_id, db)

@router.post("/orders/create_from_chat", response_model=dict)
async def create_order_from_chat(order_data: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        if isinstance(order_data.producto, str):
            order_data.producto = OrderService.parse_product_input(order_data.producto)

        return await OrderService.create_order(order_data, db)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error al crear la orden desde el chat: {e}")
        raise HTTPException(status_code=500, detail="Error al crear la orden.")


@router.get("/orders/all/", response_model=List[schemas.OrderResponse])
async def get_all_orders(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """Obtiene todas las órdenes."""
    crud_order = CRUDOrder()
    orders = crud_order.get_all_orders(db, skip=skip, limit=limit)
    return [schemas.OrderResponse(**order) for order in orders]

@router.get("/orders/export_excel/")
async def export_orders_to_excel_endpoint(db: Session = Depends(get_db), file_path: Optional[str] = None):
    file_path = await OrderService.export_orders_to_excel(db, file_path)
    return FileResponse(file_path, filename=os.path.basename(file_path))

@router.delete("/orders/delete_all")
async def delete_all_orders(db: Session = Depends(get_db)):
    try:
        CRUDOrder().delete_all_orders(db)
        return {"message": "Todas las órdenes han sido eliminadas correctamente."}
    except Exception as e:
        logging.error(f"Error al eliminar todas las órdenes: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al eliminar todas las órdenes.")