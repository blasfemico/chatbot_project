from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas
from typing import List
from app.crud import Ciudad

router = APIRouter()


@router.post("/cities/", response_model=schemas.CiudadResponse)
def create_city(city: schemas.CiudadCreate, db: Session = Depends(get_db)):
    return crud.CRUDCiudad().create_ciudad(db=db, ciudad_data=city)


@router.post("/cities/{city_id}/products", response_model=dict)
def add_products_to_city(
    city_id: int, productos: schemas.ProductoCiudadCreate, db: Session = Depends(get_db)
):
    return crud.CRUDCiudad().add_products_to_city(
        db=db, ciudad_id=city_id, productos_nombres=productos.productos
    )


@router.get("/cities/{city_id}/products", response_model=List[dict])
def get_products_for_city(city_id: int, db: Session = Depends(get_db)):
    return crud.CRUDCiudad().get_products_for_city(db=db, ciudad_id=city_id)

@router.get("/cities/all/", response_model=dict)
async def get_all_cities(db: Session = Depends(get_db)):
    ciudades = db.query(Ciudad).all()
    if not ciudades:
        return {"ciudades": []}

    ciudades_serializables = [
        {"id": ciudad.id, "nombre": ciudad.nombre} 
        for ciudad in ciudades
    ]
    return {"ciudades": ciudades_serializables}

@router.delete("/cities/{city_id}/", response_model=dict)
def delete_city(city_id: int, db: Session = Depends(get_db)):
    return crud.CRUDCiudad().delete_ciudad(db=db, ciudad_id=city_id)
