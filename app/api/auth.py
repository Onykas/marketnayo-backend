from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token, generate_otp
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

otp_store: dict = {}


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(data: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.phone == data.phone).first():
        raise HTTPException(400, "Ce numéro est déjà enregistré")

    user = models.User(
        phone=data.phone,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role.value,
        full_name=user.full_name,
        phone=user.phone,
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.phone == data.phone).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Numéro ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(403, "Compte désactivé")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role.value,
        full_name=user.full_name,
        phone=user.phone,
    )


@router.post("/send-otp")
def send_otp(data: schemas.OTPRequest):
    code = generate_otp()
    otp_store[data.phone] = code
    print(f"[OTP DEV] {data.phone} → {code}")
    return {"message": "Code envoyé"}


@router.post("/verify-otp")
def verify_otp(data: schemas.OTPVerify, db: Session = Depends(get_db)):
    stored = otp_store.get(data.phone)
    if not stored or stored != data.code:
        raise HTTPException(400, "Code invalide ou expiré")

    user = db.query(models.User).filter(models.User.phone == data.phone).first()
    if user:
        user.is_verified = True
        db.commit()

    del otp_store[data.phone]
    return {"message": "Numéro vérifié"}