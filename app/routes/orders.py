# app/routes/orders.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app import schemas
from app.crud import CRUDOrder
from app.database import get_db

router = APIRouter()

# Crear un nuevo pedido
@router.post("/orders/", response_model=schemas.Order)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        crud_order = CRUDOrder()
        new_order = crud_order.create_order(db=db, order=order)
        return new_order
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear el pedido: {str(e)}")

# Obtener todos los pedidos
@router.get("/orders/", response_model=list[schemas.Order])
async def get_orders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    try:
        crud_order = CRUDOrder()
        orders = crud_order.get_all_orders(db=db, skip=skip, limit=limit)
        return orders
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener los pedidos: {str(e)}")
