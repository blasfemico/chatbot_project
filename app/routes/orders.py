from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, config, models, schemas
from app.database import get_db

router = APIRouter()

@router.post("/")
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        return crud.CRUDOrder(models.Order).create_order(db=db, order=order)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear el pedido: {str(e)}")
