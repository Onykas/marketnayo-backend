from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Enum, Text, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    vendeur = "vendeur"
    acheteur = "acheteur"
    admin = "admin"
    gestionnaire = "gestionnaire"


class OrderStatus(str, enum.Enum):
    en_attente = "en_attente"
    confirme = "confirme"
    preparation = "preparation"
    en_livraison = "en_livraison"
    proche = "proche"
    livre = "livre"
    annule = "annule"


class NegotiationStatus(str, enum.Enum):
    ouvert = "ouvert"
    accepte = "accepte"
    refuse = "refuse"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.acheteur)
    avatar_url = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    market = relationship("Market", back_populates="vendors")
    products = relationship("Product", back_populates="vendor")
    sent_messages = relationship("ChatMessage", foreign_keys="ChatMessage.sender_id", back_populates="sender")
    orders_as_buyer = relationship("Order", foreign_keys="Order.buyer_id", back_populates="buyer")
    orders_as_seller = relationship("Order", foreign_keys="Order.seller_id", back_populates="seller")


class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False)
    address = Column(String(255))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendors = relationship("User", back_populates="market")
    products = relationship("Product", back_populates="market")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    unit = Column(String(20), default="kg")
    stock_quantity = Column(Float, default=0)
    min_order = Column(Float, default=1)
    image_url = Column(String(255), nullable=True)
    is_available = Column(Boolean, default=True)
    is_negotiable = Column(Boolean, default=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = relationship("User", back_populates="products")
    market = relationship("Market", back_populates="products")
    category = relationship("Category", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="price_history")


class ChatConversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="conversation")
    negotiations = relationship("Negotiation", back_populates="conversation")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("ChatConversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")


class Negotiation(Base):
    __tablename__ = "negotiations"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    proposed_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    status = Column(Enum(NegotiationStatus), default=NegotiationStatus.ouvert)
    proposed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("ChatConversation", back_populates="negotiations")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="en_attente")
    total_amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="cash")
    payment_status = Column(String(20), default="pending")
    delivery_address = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="orders_as_buyer")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="orders_as_seller")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class DeletedConversation(Base):
    __tablename__ = "deleted_conversations"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime, default=datetime.utcnow)