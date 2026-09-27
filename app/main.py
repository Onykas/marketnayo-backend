from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.api import auth, products, chat, orders

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MarketNaYo API",
    description="Le marché, version smart.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(chat.router)
app.include_router(orders.router)

@app.get("/")
def root():
    return {"message": "MarketNaYo API v1.0", "docs": "/docs"}

@app.get("/api/dashboard")
def dashboard_stats():
    return {
        "total_products": 0,
        "total_orders": 0,
        "total_users": 0,
    }