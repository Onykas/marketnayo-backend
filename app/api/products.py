from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["Marchés & Produits"])


# ── Marchés ───────────────────────────────────────────

@router.get("/markets", response_model=List[schemas.MarketOut])
def list_markets(
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Market).filter(models.Market.is_active == True)
    if city:
        q = q.filter(models.Market.city.ilike(f"%{city}%"))
    return q.all()


@router.get("/markets/{market_id}", response_model=schemas.MarketOut)
def get_market(market_id: int, db: Session = Depends(get_db)):
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market:
        raise HTTPException(404, "Marché non trouvé")
    return market


@router.post("/markets", response_model=schemas.MarketOut, status_code=201)
def create_market(
    data: schemas.MarketCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role.value not in ("admin", "gestionnaire"):
        raise HTTPException(403, "Accès refusé")
    market = models.Market(**data.dict())
    db.add(market)
    db.commit()
    db.refresh(market)
    return market


# ── Produits ──────────────────────────────────────────

@router.get("/products", response_model=List[schemas.ProductOut])
def list_products(
    market_id: Optional[int] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    q = db.query(models.Product).filter(models.Product.is_available == True)
    if market_id:
        q = q.filter(models.Product.market_id == market_id)
    if category_id:
        q = q.filter(models.Product.category_id == category_id)
    if search:
        q = q.filter(models.Product.name.ilike(f"%{search}%"))
    if min_price is not None:
        q = q.filter(models.Product.price >= min_price)
    if max_price is not None:
        q = q.filter(models.Product.price <= max_price)
    return q.offset(skip).limit(limit).all()


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Produit non trouvé")
    return product


@router.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(
    data: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role.value not in ("vendeur", "admin"):
        raise HTTPException(403, "Seuls les vendeurs peuvent créer des produits")

    product = models.Product(**data.dict(), vendor_id=current_user.id)
    db.add(product)

    db.flush()
    price_entry = models.PriceHistory(product_id=product.id, price=data.price)
    db.add(price_entry)

    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Produit non trouvé")
    if product.vendor_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(403, "Vous ne pouvez modifier que vos propres produits")

    update_data = data.dict(exclude_unset=True)

    if "price" in update_data and update_data["price"] != product.price:
        db.add(models.PriceHistory(product_id=product.id, price=update_data["price"]))

    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Produit non trouvé")
    if product.vendor_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(403, "Accès refusé")

    product.is_available = False
    db.commit()


@router.get("/products/{product_id}/price-history")
def price_history(product_id: int, db: Session = Depends(get_db)):
    history = (
        db.query(models.PriceHistory)
        .filter(models.PriceHistory.product_id == product_id)
        .order_by(models.PriceHistory.recorded_at.desc())
        .limit(30)
        .all()
    )
    return [{"price": h.price, "date": h.recorded_at} for h in history]


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()


@router.delete("/{product_id}")
def delete_product_alt(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Produit non trouvé")
    if product.vendor_id != current_user.id:
        raise HTTPException(403, "Vous ne pouvez supprimer que vos propres produits")
    db.delete(product)
    db.commit()
    return {"message": "Produit supprimé"}