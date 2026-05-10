import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database Configuration (K8s Env Vars)
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "ecommerce")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# SQLAlchemy Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Models ---
class ProductDB(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    image_url = Column(String)

class OrderDB(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer)
    quantity = Column(Integer)
    status = Column(String, default="pending")

# Create Tables
Base.metadata.create_all(bind=engine)

# --- Pydantic Models (API Schema) ---
class Product(BaseModel):
    name: str
    description: str
    price: float
    image_url: str

class ProductCreate(Product):
    pass

class ProductResponse(Product):
    id: int
    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    product_id: int
    quantity: int

# --- API Implementation ---
app = FastAPI(title="E-Commerce Product Service")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Cloud-Native E-Commerce API"}

@app.get("/products", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(ProductDB).all()

@app.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = ProductDB(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.post("/orders")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # 1. Check if product exists
    product = db.query(ProductDB).filter(ProductDB.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 2. Create Order
    new_order = OrderDB(product_id=order.product_id, quantity=order.quantity, status="processing")
    db.add(new_order)
    db.commit()
    
    # TODO: Phase 4 - Send event to Redis Queue here!
    
    return {"message": "Order placed successfully", "order_id": new_order.id}
