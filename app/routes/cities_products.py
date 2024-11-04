# app/routes/cities_products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas, models
from app.database import get_db

router = APIRouter()

# Ruta para crear una nueva ciudad
@router.post("/cities/", response_model=schemas.City)
def create_city(city: schemas.CityCreate, db: Session = Depends(get_db)):
    return crud.CRUDCity().create_city(db, city)

# Ruta para obtener todas las ciudades
@router.get("/cities/", response_model=list[schemas.City])
def get_all_cities(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.CRUDCity().get_all_cities(db, skip=skip, limit=limit)

# Ruta para obtener una ciudad por ID
@router.get("/cities/{city_id}", response_model=schemas.City)
def get_city_by_id(city_id: int, db: Session = Depends(get_db)):
    city = crud.CRUDCity().get_city_by_id(db, city_id)
    if not city:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    return city

# Ruta para eliminar una ciudad
@router.delete("/cities/{city_id}")
def delete_city(city_id: int, db: Session = Depends(get_db)):
    city = crud.CRUDCity().delete_city(db, city_id)
    if not city:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    return {"message": f"La ciudad con ID {city_id} ha sido eliminada exitosamente."}

# Ruta para crear un producto en una ciudad específica
@router.post("/cities/{city_id}/products/", response_model=schemas.Product)
def create_product(city_id: int, product: schemas.ProductCreate, db: Session = Depends(get_db)):
    city = crud.CRUDCity().get_city_by_id(db, city_id)
    if not city:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    return crud.CRUDProduct().create_product(db, product, city_id)

# Ruta para obtener todos los productos de una ciudad específica
@router.get("/cities/{city_id}/products/", response_model=list[schemas.Product])
def get_products_by_city(city_id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    city = crud.CRUDCity().get_city_by_id(db, city_id)
    if not city:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    return crud.CRUDProduct().get_products_by_city(db, city_id, skip=skip, limit=limit)

# Ruta para obtener un producto por ID
@router.get("/products/{product_id}", response_model=schemas.Product)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

# Ruta para eliminar un producto
@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.CRUDProduct().delete_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": f"El producto con ID {product_id} ha sido eliminado exitosamente."}
