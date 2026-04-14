from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
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
    
    logger.info(f"MongoDB connection string loaded successfully")
    return uri

uri = load_mongo_uri()

client = AsyncIOMotorClient(uri)
db = client['qab']
logger.info(f"Async MongoDB client initialized for database: qab")

users_collection = db['users']
agents_collection = db['agents']
logger.info(f"MongoDB collections initialized: users, agents")

# SYNC CLIENT
vec_client = MongoClient(os.getenv("MONGO_URI"))
vec_db = vec_client["qab"]
vector_collection = vec_db["embeddings"]  # sync (for LangChain)
logger.info(f"Sync MongoDB vector collection initialized: vector_store")

