from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud
from app.database import get_db
from typing import List
from app.models import Cuenta
from app.crud import CuentaCreate
from app import schemas
router = APIRouter()


@router.post("/accounts/")
async def create_account(account_data: CuentaCreate, db: Session = Depends(get_db)):
    cuenta = Cuenta(nombre=account_data.nombre, page_id=account_data.page_id)
    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return {"message": "Cuenta creada con éxito", "id": cuenta.id}

@router.get(
    "/accounts/{account_id}/products",
    response_model=List[schemas.ProductoCuentaResponse],
)
def get_products_for_account(account_id: int, db: Session = Depends(get_db)):
    """Obtiene todos los productos y precios de una cuenta específica"""
    productos = crud.CRUDCuentaProducto().get_products_for_account(db=db, cuenta_id=account_id)
    return productos




@router.post("/accounts/{account_id}/products", response_model=dict)
def add_products_to_account(
    account_id: int,
    productos: schemas.ProductosCuentaCreate,
    db: Session = Depends(get_db),
):
    """Asocia productos a una cuenta con precios específicos"""
    return crud.CRUDCuentaProducto().add_products_to_account(
        db=db, cuenta_id=account_id, productos_data=productos
    )


@router.put(
    "/accounts/{account_id}/products/{product_id}",
    response_model=schemas.CuentaProducto,
)
async def update_product_price_for_account(
    account_id: int, product_id: int, price: float, db: Session = Depends(get_db)
):
    """Actualiza el precio de un producto en una cuenta específica."""
    return crud.CRUDCuentaProducto().update_product_price_for_account(
        db=db, cuenta_id=account_id, producto_id=product_id, new_price=price
    )


@router.delete("/accounts/{account_id}/products/{product_id}")
async def delete_product_from_account(
    account_id: int, product_id: int, db: Session = Depends(get_db)
):
    """Elimina un producto específico de una cuenta."""
    return crud.CRUDCuentaProducto().remove_product_from_account(
        db=db, cuenta_id=account_id, producto_id=product_id
    )

@router.get("/accounts/all", response_model=List[schemas.Cuenta])
async def get_all_accounts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Obtiene todas las cuentas existentes con paginación.
    """
    return crud.CRUDCuenta().get_all_cuentas(db=db, skip=skip, limit=limit)

@router.delete("/accounts/{account_id}/delete")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    cuenta = db.query(Cuenta).filter(Cuenta.id == account_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    db.delete(cuenta)
    db.commit()
    return {"message": "Cuenta eliminada con éxito."}
