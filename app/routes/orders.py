# app/routes/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas
from app.database import get_db

router = APIRouter()

# Ruta para crear un pedido
@router.post("/orders/")
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        return crud.CRUDOrder().create_order(db=db, order=order)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear el pedido: {str(e)}")

# Ruta para obtener todos los pedidos
@router.get("/orders/", response_model=list[schemas.Order])
async def get_orders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    try:
        return crud.CRUDOrder().get_orders(db=db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener los pedidos: {str(e)}")
