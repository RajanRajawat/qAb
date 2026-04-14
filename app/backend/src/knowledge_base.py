from fastapi import APIRouter, File, UploadFile, Depends, BackgroundTasks
import os, shutil
from database.db import users_collection, vector_collection
from utils.users import get_current_user
from utils.response import success_response, error_response
from utils.loggers import logger
from bson import ObjectId

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient


kb_router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


#- Helper: Resolve target vector collection
def get_target_collection(custom_db_settings: dict = None, owner_id: str = ""):
    if custom_db_settings and custom_db_settings.get('linked') is True:
        mongo_settings = custom_db_settings.get('mongo_db', {})
        connection_string = mongo_settings.get('connection_string')
        db_name = mongo_settings.get('db_name')
        collection_name = mongo_settings.get('collection_name')

        if connection_string and db_name and collection_name:
            try:
                custom_client = MongoClient(connection_string)
                logger.info(f"Using custom DB for owner {owner_id}")
                return custom_client[db_name][collection_name]
            except Exception as e:
                logger.error(f"Failed to connect to custom DB for owner {owner_id}: {e}")

    return vector_collection


#- Background Task: Process file and embed into MongoDB
def process_file_and_embed(file_path: str, file_name: str, owner_id: str, custom_db_settings: dict = None):
    try:
        logger.info(f"Processing file: {file_name} for owner: {owner_id}")

        # Load
        if file_name.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        documents = loader.load()

        # Split
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,      
            chunk_overlap=50,
        )
        chunks = splitter.split_documents(documents)

        # Tag each chunk with owner_id as ObjectId
        for chunk in chunks:
            chunk.metadata['owner_id'] = ObjectId(owner_id)

        # Embeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        # DB Connection
        target_collection = get_target_collection(custom_db_settings, owner_id)

        # Store
        MongoDBAtlasVectorSearch.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection=target_collection,
            index_name="vector_index_qab"
        )
        
        logger.info(f"Successfully embedded {len(chunks)} chunks for file: {file_name} (Owner: {owner_id})")
    
    except Exception as e:
        logger.error(f"Error processing document {file_name}: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@kb_router.post("/upload")
async def upload_document(
    bt: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Knowledge Base upload request from {current_user['email']}")
    
    if not file.filename.endswith(('.txt', '.pdf')):
        return error_response(400, message="Only .txt and .pdf files are supported")
        
    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(404, message="User not found")
        
    
    
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", f"{current_user['_id']}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    custom_db = user_data.get('custom_db', {})
   
   
    bt.add_task(
        process_file_and_embed,
        file_path,
        file.filename,
        str(current_user['_id']),
        custom_db
    )
    
    logger.info(f"File {file.filename} queued for processing (Owner: {current_user['email']})")
    return success_response(202, message="File uploaded successfully. Processing in background.")
