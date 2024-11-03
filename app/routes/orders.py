from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import CRUDOrder, CRUDProduct
from app.schemas import OrderCreate, MessageCreate
from app.utils import get_facebook_user_name
router = APIRouter()

crud_order = CRUDOrder()

@router.post("/order/")
def process_message(message: MessageCreate, db: Session = Depends(get_db)):
    if not message.phone:
        raise HTTPException(status_code=400, detail="Phone number is required to create an order.")
    
    # Obtener el nombre del cliente desde Facebook usando el ADID
    customer_name = get_facebook_user_name(message.customer_adid, "YOUR_ACCESS_TOKEN")
    
    product = crud_order.get_product_from_message(db=db, message=message.content)
    if product is None:
        raise HTTPException(status_code=404, detail="No product found in message content.")
    
    # Crear la orden con el nombre del cliente desde Facebook
    order_data = OrderCreate(
        phone=message.phone,
        address=message.address,
        customer_name=customer_name,
        product_id=product.id,
        total_price=product.price
    )
    order = crud_order.create_order(db=db, order_data=order_data)
    return order