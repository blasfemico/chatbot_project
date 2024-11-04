# app/routes/orders.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app import schemas
from app.crud import CRUDOrder
from app.database import get_db

router = APIRouter()

# Crear un nuevo pedido
@router.post("/", response_model=schemas.Order)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        crud_order = CRUDOrder()
        new_order = crud_order.create_order(db=db, order=order)
        return new_order
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear el pedido: {str(e)}")

# Obtener todos los pedidos
@router.get("/", response_model=list[schemas.Order])
async def get_orders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    try:
        crud_order = CRUDOrder()
        orders = crud_order.get_all_orders(db=db, skip=skip, limit=limit)
        return orders
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener los pedidos: {str(e)}")

# Obtener un pedido por su ID
@router.get("/{order_id}", response_model=schemas.Order)
async def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    try:
        crud_order = CRUDOrder()
        order = crud_order.get_order_by_id(db=db, order_id=order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener el pedido: {str(e)}")
