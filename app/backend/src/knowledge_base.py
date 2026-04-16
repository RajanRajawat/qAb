

#~ Ingest RAG                                           
#: Todo:                                                
#:  Embedding Model Inference (Done)                    
#! Bugs:                                                
#- Notes:                                               


from fastapi import APIRouter, File, UploadFile, Depends, BackgroundTasks
from pydantic import SecretStr
import os, shutil
from database.db import users_collection, vector_collection
from utils.users import get_current_user
from utils.response import success_response, error_response
from utils.loggers import logger
from bson import ObjectId
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpointEmbeddings
# from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_postgres import PGVector
from utils.env_loaders import load_hf_api
from pymongo import MongoClient


kb_router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


#- Helper: Resolve target vector collection (Mongo only — Postgres handled separately)
def get_target_collection(custom_db_settings: dict = None, owner_id: str = ""):
    if custom_db_settings and custom_db_settings.get('linked') is True:
        provider = custom_db_settings.get('provider')
        config = custom_db_settings.get('config', {})
        connection_string = config.get('connection_string')

        if provider == 'mongo':
            db_name = config.get('db_name')
            collection_name = config.get('collection_name')

            if connection_string and db_name and collection_name:
                try:
                    custom_client = MongoClient(connection_string)
                    logger.info(f"Using custom MongoDB for owner {owner_id}")
                    return custom_client[db_name][collection_name]
                except Exception as e:
                    logger.error(f"Failed to connect to custom MongoDB for owner {owner_id}: {e}")

    return vector_collection


#- Background Task: Process file and embed into MongoDB
def process_file_and_embed(file_path: str, file_name: str, owner_id: str, custom_db_settings: dict = None):
    try:
        logger.info(f"Processing file: {file_name} for owner: {owner_id}")

        if file_name.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )
        chunks = splitter.split_documents(documents)

        for chunk in chunks:
            chunk.metadata['owner_id'] = str(owner_id) #storing in STR for Postgres use

        # embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2") #replace with hf inference api
        embeddings = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=(load_hf_api()),
        )

        provider = custom_db_settings.get('provider') if custom_db_settings else None
        config = custom_db_settings.get('config', {}) if custom_db_settings else {}

        if custom_db_settings and custom_db_settings.get('linked') is True and provider == 'postgres':
            connection_string = config.get('connection_string')
            try:
                logger.info(f"Using custom Postgres (pgvector) for owner {owner_id}")
                PGVector.from_documents(
                        documents=chunks,
                        embedding=embeddings,
                        collection_name=f"embeddings",
                        connection=connection_string,
                        use_jsonb=True,
                    )
                logger.info(f"Successfully embedded {len(chunks)} chunks into Postgres for file: {file_name} (Owner: {owner_id})")
            except Exception as e:
                logger.error(f"Failed to embed into Postgres for owner {owner_id}: {e}")
        else:
            target_collection = get_target_collection(custom_db_settings, owner_id)
            _embed_mongo(chunks, embeddings, owner_id, file_name, target_collection)

    except Exception as e:
        logger.error(f"Error processing file {file_name} for owner {owner_id}: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


#- Helper: Embed into a MongoDB Atlas vector collection
def _embed_mongo(chunks, embeddings, owner_id, file_name, target_collection=None):
    if target_collection is None:
        target_collection = vector_collection
    try:
        MongoDBAtlasVectorSearch.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection=target_collection,
            index_name="vector_index_qab"
        )
        logger.info(f"Successfully embedded {len(chunks)} chunks into MongoDB for file: {file_name} (Owner: {owner_id})")
    except Exception as e:
        logger.error(f"Failed to embed into MongoDB for owner {owner_id}: {e}")


@kb_router.post("/upload")
async def upload_document(
    bt: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Knowledge Base upload request received from {current_user['email']}")

    if not file.filename.endswith(('.txt', '.pdf')):
        return error_response(400, message="Only .txt and .pdf files are supported.")

    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(404, message="User not found.")

    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", f"{file.filename}")

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

    logger.info(f"File '{file.filename}' queued for processing (Owner: {current_user['email']})")
    return success_response(202, message="File uploaded successfully. Processing in background.")




#need to check pg!