from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas
from app.database import get_db
from typing import List

router = APIRouter()


@router.post("/accounts/", response_model=schemas.Cuenta)
async def create_account(account: schemas.CuentaCreate, db: Session = Depends(get_db)):
    """Crea una cuenta en la base de datos utilizando el page_id de Facebook."""
    existing_account = (
        db.query(crud.Cuenta).filter(crud.Cuenta.page_id == account.page_id).first()
    )
    if existing_account:
        raise HTTPException(
            status_code=400, detail="Ya existe una cuenta con este page_id."
        )

    return crud.CRUDCuenta().create_cuenta(db=db, cuenta_data=account)


@router.get(
    "/accounts/{account_id}/products",
    response_model=List[schemas.ProductoCuentaResponse],
)
def get_products_for_account(account_id: int, db: Session = Depends(get_db)):
    """Obtiene todos los productos y precios de una cuenta específica"""
    return crud.CRUDCuentaProducto().get_products_for_account(
        db=db, cuenta_id=account_id
    )


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

