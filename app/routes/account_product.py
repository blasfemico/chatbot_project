from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas, models
from app.database import get_db

router = APIRouter()

# Ruta para crear una nueva cuenta
@router.post("/cuentas/", response_model=schemas.Cuenta)
def create_cuenta(cuenta: schemas.CuentaCreate, db: Session = Depends(get_db)):
    return crud.CRUDCuenta().create_cuenta(db, cuenta)

# Ruta para obtener todas las cuentas
@router.get("/cuentas/", response_model=list[schemas.Cuenta])
def get_all_cuentas(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.CRUDCuenta().get_all_cuentas(db, skip=skip, limit=limit)

# Ruta para obtener una cuenta por ID
@router.get("/cuentas/{cuenta_id}", response_model=schemas.Cuenta)
def get_cuenta_by_id(cuenta_id: int, db: Session = Depends(get_db)):
    cuenta = crud.CRUDCuenta().get_cuenta_by_id(db, cuenta_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return cuenta

# Ruta para asociar un producto con una cuenta y especificar un precio
@router.post("/cuentas/{cuenta_id}/productos/", response_model=schemas.CuentaProducto)
def add_producto_to_cuenta(cuenta_id: int, producto: schemas.ProductoCreate, precio: float, db: Session = Depends(get_db)):
    return crud.CRUDCuentaProducto().add_producto_to_cuenta(db, cuenta_id, producto, precio)

# Ruta para obtener todos los productos de una cuenta específica
@router.get("/cuentas/{cuenta_id}/productos/", response_model=list[schemas.CuentaProducto])
def get_productos_by_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    productos = crud.CRUDCuentaProducto().get_productos_by_cuenta(db, cuenta_id)
    if not productos:
        raise HTTPException(status_code=404, detail="No se encontraron productos para esta cuenta")
    return productos
