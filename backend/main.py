from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import time
import logging
from urllib.parse import quote_plus

app = FastAPI(title="TechStock", description="IT Equipment Inventory Manager")
MONGO_DB = os.getenv("MONGO_DB", "techstock_db")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://techstock.local", "http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_mongo_uri():
    username = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    if not username or not password:
        raise RuntimeError("MONGO_INITDB_ROOT_USERNAME and MONGO_INITDB_ROOT_PASSWORD must be set")
    host = os.getenv("MONGO_HOST", "localhost")
    return f"mongodb://{quote_plus(username)}:{quote_plus(password)}@{host}:27017/{MONGO_DB}?authSource=admin"

def connect_to_mongo(max_retries=5, retry_delay=5):
    uri = get_mongo_uri()
    logger.info("Attempting to connect to MongoDB")
    for attempt in range(max_retries):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.server_info()  
            logger.info("Successfully connected to MongoDB")
            return client
        except Exception as e:
            logger.error("MongoDB connection attempt %s/%s failed (%s)", attempt + 1, max_retries, type(e).__name__)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise RuntimeError("Failed to connect to MongoDB after retries") from None
    raise Exception("Failed to connect to MongoDB after retries")

try:
    client = connect_to_mongo()
    db = client[MONGO_DB]
    items_collection = db.items
except Exception as e:
    logger.error("Failed to establish MongoDB connection (%s)", type(e).__name__)
    raise

class Item(BaseModel):
    name: str
    price: float
    quantity: int = 0

@app.on_event("startup")
async def seed_data():
    try:
        if items_collection.count_documents({}) == 0:
            initial_items = [
                {"name": "Dell Latitude Laptop", "price": 899.0, "quantity": 10},
                {"name": "24-inch Monitor", "price": 179.0, "quantity": 5},
                {"name": "Mechanical Keyboard", "price": 79.0, "quantity": 15},
            ]
            items_collection.insert_many(initial_items)
            logger.info("Seeded initial data")
    except Exception as e:
        logger.error(f"Seeding failed: {str(e)}")

@app.get("/api/items")
async def get_items():
    try:
        items = []
        for item in items_collection.find():
            item["_id"] = str(item["_id"])
            items.append(item)
        return items
    except Exception as e:
        logger.error(f"Get items failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/items")
async def add_item(item: Item):
    try:
        result = items_collection.insert_one(item.dict())
        return {"id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Add item failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/items/{item_id}")
async def update_item(item_id: str, item: Item):
    try:
        result = items_collection.update_one({"_id": ObjectId(item_id)}, {"$set": item.dict()})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Item updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update item failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/items/{item_id}")
async def delete_item(item_id: str):
    try:
        result = items_collection.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Item deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete item failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/items/{item_id}/quantity")
async def update_quantity(item_id: str, action: str = Query(..., description="add or remove")):
    if action not in ["add", "remove"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    try:
        inc = 1 if action == "add" else -1
        result = items_collection.update_one({"_id": ObjectId(item_id)}, {"$inc": {"quantity": inc}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"message": "Quantity updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update quantity failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)