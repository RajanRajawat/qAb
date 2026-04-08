from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

import os, logging

#- Logger
logging.basicConfig(
    filename="qab_logs.txt",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

def get_logger(name: str):
    return logging.getLogger(name) 

logger = get_logger(__name__)
load_dotenv()

def load_mongo_uri():
    uri = os.getenv("MONGO_URI")
    if not uri:
        logger.error(f"MongoDB connection string not found in .env file")
        return None
    
    return uri

uri = load_mongo_uri()

client = AsyncIOMotorClient(uri)
db = client['qab']

users_collection = db['users']