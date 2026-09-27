from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models import UserRole, NegotiationStatus


# ── Auth ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    phone: str
    full_name: str
    password: str
    role: UserRole = UserRole.acheteur
    email: Optional[EmailStr] = None

class LoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    full_name: Optional[str] = None
    phone: Optional[str] = None

class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    code: str


# ── User ──────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    phone: str
    full_name: str
    email: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        orm_mode = True


# ── Market ────────────────────────────────────────────

class MarketCreate(BaseModel):
    name: str
    city: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    description: Optional[str]

class MarketOut(MarketCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


# ── Product ───────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    description: Optional[str]
    price: float
    unit: str = "kg"
    stock_quantity: float
    min_order: float = 1
    is_negotiable: bool = True
    market_id: int
    category_id: Optional[int]

class ProductUpdate(BaseModel):
    name: Optional[str]
    price: Optional[float]
    stock_quantity: Optional[float]
    is_available: Optional[bool]

class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    unit: str
    stock_quantity: float
    is_available: bool
    is_negotiable: bool
    vendor_id: int
    vendor: UserOut
    market: MarketOut
    created_at: datetime

    class Config:
        orm_mode = True


# ── Chat ──────────────────────────────────────────────

class MessageCreate(BaseModel):
    conversation_id: int
    content: str
    message_type: str = "text"

class MessageOut(BaseModel):
    id: int
    sender_id: int
    content: str
    message_type: str
    is_read: bool
    created_at: datetime

    class Config:
        orm_mode = True

class ConversationOut(BaseModel):
    id: int
    buyer_id: int
    seller_id: int
    product_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


# ── Negotiation ───────────────────────────────────────

class NegotiationCreate(BaseModel):
    conversation_id: int
    proposed_price: float
    quantity: float

class NegotiationOut(BaseModel):
    id: int
    proposed_price: float
    quantity: float
    status: NegotiationStatus
    proposed_by_id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ── Order ─────────────────────────────────────────────

class OrderItemIn(BaseModel):
    product_id: int
    quantity: float
    unit_price: float

class OrderCreate(BaseModel):
    seller_id: int
    items: List[OrderItemIn]
    payment_method: str = "cash"
    delivery_address: Optional[str]
    notes: Optional[str]

class OrderOut(BaseModel):
    id: int
    buyer_id: int
    seller_id: int
    status: str
    total_amount: float
    payment_method: str
    payment_status: str
    created_at: datetime

    class Config:
        orm_mode = True