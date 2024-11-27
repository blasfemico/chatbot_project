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

@router.delete("/cities/{city_id}/products/{product_id}", response_model=dict)
def delete_product_from_city(
    city_id: int, product_id: int, db: Session = Depends(get_db)
):
    """
    Elimina un producto específico de una ciudad.
    """
    try:
        result = crud.CRUDCiudad().delete_product_from_city(
            db=db, ciudad_id=city_id, producto_id=product_id
        )
        if result:
            return {"message": f"Producto con ID {product_id} eliminado de la ciudad con ID {city_id}"}
        else:
            raise HTTPException(status_code=404, detail="Producto no encontrado en la ciudad")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cities/{city_id}/products/delete_all", response_model=dict)
def delete_all_products_from_city(city_id: int, db: Session = Depends(get_db)):
    """
    Elimina todos los productos asociados a una ciudad.
    """
    try:
        result = crud.CRUDCiudad().delete_all_products_from_city(db=db, ciudad_id=city_id)
        return {"message": f"Todos los productos de la ciudad con ID {city_id} han sido eliminados"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
