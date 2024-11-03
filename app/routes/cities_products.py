from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import CRUDCity, CRUDProduct
from app.schemas import CityCreate, ProductCreate

router = APIRouter()


crud_city = CRUDCity()
crud_product = CRUDProduct()

@router.post("/cities/", response_model=CityCreate)
def create_city(city: CityCreate, db: Session = Depends(get_db)):
    db_city = crud_city.create_city(db=db, city=city)
    return db_city

@router.get("/cities/")
def get_all_cities(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud_city.get_all_cities(db=db, skip=skip, limit=limit)

@router.post("/cities/{city_id}/products/", response_model=ProductCreate)
def create_product_for_city(city_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    # Verificar si la ciudad existe
    db_city = crud_city.get_city_by_id(db=db, city_id=city_id)
    if db_city is None:
        raise HTTPException(status_code=404, detail="City not found")
    
    db_product = crud_product.create_product(db=db, product=product, city_id=city_id)
    return db_product

@router.get("/cities/{city_id}/products/")
def get_products_by_city(city_id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):

    db_city = crud_city.get_city_by_id(db=db, city_id=city_id)
    if db_city is None:
        raise HTTPException(status_code=404, detail="City not found")
    
    return crud_product.get_products_by_city(db=db, city_id=city_id, skip=skip, limit=limit)
