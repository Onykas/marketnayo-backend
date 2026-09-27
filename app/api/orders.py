from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/orders", tags=["Commandes"])


@router.post("", response_model=schemas.OrderOut, status_code=201)
def create_order(
    data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    total = sum(item.quantity * item.unit_price for item in data.items)

    order = models.Order(
        buyer_id=current_user.id,
        seller_id=data.seller_id,
        total_amount=total,
        payment_method=data.payment_method,
        delivery_address=data.delivery_address,
        notes=data.notes,
    )
    db.add(order)
    db.flush()

    for item in data.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id).first()
        if not product:
            # Créer un item sans produit si non trouvé
            db.add(models.OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            ))
            continue

        db.add(models.OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        ))

    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=List[schemas.OrderOut])
def my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return (
        db.query(models.Order)
        .filter(
            (models.Order.buyer_id == current_user.id) |
            (models.Order.seller_id == current_user.id)
        )
        .order_by(models.Order.created_at.desc())
        .all()
    )


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Commande non trouvée")
    if order.buyer_id != current_user.id and order.seller_id != current_user.id:
        raise HTTPException(403, "Accès refusé")
    return order


@router.patch("/{order_id}/status")
def update_status(
    order_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Commande non trouvée")
    order.status = new_status
    db.commit()
    return {"status": new_status, "message": "Statut mis à jour"}


@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Commande non trouvée")
    if order.buyer_id != current_user.id and order.seller_id != current_user.id:
        raise HTTPException(403, "Accès refusé")
    db.query(models.OrderItem).filter(
        models.OrderItem.order_id == order_id).delete()
    db.delete(order)
    db.commit()
    return {"message": "Commande supprimée"}