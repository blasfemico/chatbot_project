from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app import schemas
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

router = APIRouter()

class OrderService:
   
    @staticmethod
    def get_safe_file_path(directory: str, filename: str = "ordenes_exportadas.xlsx") -> str:
        # Limpiar el nombre del archivo para que solo tenga caracteres seguros
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)
        filename = filename if filename.endswith(".xlsx") else f"{filename}.xlsx"
        
        # Construir la ruta completa
        file_path = os.path.join(directory, filename)
        
        return file_path
   
    @staticmethod
    async def create_order(order_data: schemas.OrderCreate, db: Session, nombre: str = "N/A", apellido: str = "N/A") -> dict:
        try:
            crud_order = CRUDOrder()
            new_order = crud_order.create_order(db=db, order=order_data, nombre=nombre, apellido=apellido)
            delivery_message = CRUDOrder.get_delivery_day_message()
            return {
                "message": f"Gracias por su pedido. {delivery_message}",
                "order": new_order
            }
        except Exception as e:
            logging.error(f"Error al crear la orden: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al crear el pedido.")




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
    async def get_all_orders(db: Session) -> List[schemas.OrderResponse]:
        orders = CRUDOrder().get_all_orders(db=db)
        return [
            {
                "id": order.id,
                "phone": order.phone or "N/A",      # Valor predeterminado
                "email": order.email or "N/A",      # Valor predeterminado
                "address": order.address or "N/A",  # Valor predeterminado
                "producto": order.producto,
                "cantidad_cajas": order.cantidad_cajas,
                "nombre": order.nombre,
                "apellido": order.apellido,
                "ad_id": order.ad_id,
            }
            for order in orders
        ]
    
    @staticmethod
    async def export_orders_to_excel(db: Session, file_path: Optional[str]) -> str:
        # Crear un directorio temporal para el archivo si no se proporciona una ruta
        if not file_path:
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, "ordenes_exportadas.xlsx")
        else:
            # Validar y construir una ruta segura
            file_path = OrderService.get_safe_file_path(file_path)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Órdenes"

        # Añadir los encabezados, incluyendo los nuevos campos
        headers = ["ID", "Teléfono", "Email", "Dirección", "Producto", "Cantidad", "Ad ID", "Nombre", "Apellido"]
        sheet.append(headers)
        
        # Obtener todas las órdenes
        orders = CRUDOrder().get_all_orders(db)
        for order in orders:
            sheet.append([
                order["id"],
                order["phone"] or "N/A",
                order["email"] or "N/A",
                order["address"] or "N/A",
                order["producto"],
                order["cantidad_cajas"],
                order.get("ad_id", "N/A"),  # Ad ID con valor predeterminado "N/A" si es None
                order.get("nombre", "N/A"),  # Nombre con valor predeterminado "N/A" si es None
                order.get("apellido", "N/A")  # Apellido con valor predeterminado "N/A" si es None
            ])
        
        # Guardar el archivo Excel
        workbook.save(file_path)

        # Asegurarse de que el archivo tiene permisos restrictivos
        os.chmod(file_path, 0o600)  # Solo lectura y escritura para el propietario
        
        return file_path


@router.post("/orders/", response_model=dict)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    return await OrderService.create_order(order, db)

@router.get("/orders/{order_id}", response_model=schemas.OrderResponse)
async def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    return await OrderService.get_order_by_id(order_id, db)

@router.get("/", response_model=List[schemas.Order])
async def get_orders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return await OrderService.get_orders(skip, limit, db)

@router.delete("/orders/{order_id}", response_model=dict)
async def delete_order(order_id: int, db: Session = Depends(get_db)):
    return await OrderService.delete_order(order_id, db)

@router.post("/orders/create_from_chat", response_model=Dict[str, str])
async def create_order_from_chat(order_data: schemas.OrderCreate, db: Session = Depends(get_db)):
    return await OrderService.create_order(order_data, db)

@router.get("/orders/all/", response_model=List[schemas.OrderResponse])
async def get_all_orders(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    orders = CRUDOrder().get_all_orders(db=db, skip=skip, limit=limit)
    return [
        {
            "id": order["id"],                 # Cambiar "order.id" a "order['id']" si order es un diccionario
            "phone": order["phone"] or "N/A",   # Acceder a los valores como diccionario
            "email": order["email"] or "N/A",
            "address": order["address"] or "N/A",
            "producto": order["producto"],
            "cantidad_cajas": order["cantidad_cajas"],
            "nombre": order["nombre"],
            "apellido": order["apellido"],
            "ad_id": order["ad_id"],

        }
        for order in orders
    ]

@router.get("/orders/export_excel/")
async def export_orders_to_excel_endpoint(db: Session = Depends(get_db), file_path: Optional[str] = None):
    file_path = await OrderService.export_orders_to_excel(db, file_path)
    return FileResponse(file_path, filename=os.path.basename(file_path))