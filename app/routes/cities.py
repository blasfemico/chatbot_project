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

@router.get("/cities/all/")
async def get_all_cities(db: Session = Depends(get_db)):
    ciudades = db.query(Ciudad).all()
    if not ciudades:
        return {"respuesta": "No se encontraron ciudades."}

    # Retornamos las ciudades con la lista de productos anidada en formato JSON serializable
    ciudades_serializables = [
        {
            "id": ciudad.id,
            "nombre": ciudad.nombre,
            "productos": [{"nombre": pc.producto.nombre} for pc in ciudad.productos]
        }
        for ciudad in ciudades
    ]
    
    return {"ciudades": ciudades_serializables}