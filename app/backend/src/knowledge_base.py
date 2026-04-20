
from fastapi import APIRouter, File, UploadFile, Depends, BackgroundTasks, Query
import os, shutil
from database.db import users_collection, vector_collection, db_collection
from utils.users import get_current_user
from utils.response import success_response, error_response
from utils.loggers import logger
from bson import ObjectId
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_postgres import PGVector
from utils.env_loaders import load_hf_api
from pymongo import MongoClient


kb_router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


# ── Helper: build a raw mongo collection from a db_entry document ──────────────
def get_mongo_collection_from_entry(db_entry: dict, owner_id: str):
    config = db_entry.get('config', {})
    connection_string = config.get('connection_string')
    db_name = config.get('db_name')
    collection_name = config.get('collection_name')

    try:
        client = MongoClient(connection_string)
        logger.info(f"Connected to custom MongoDB for owner {owner_id}")
        return client[db_name][collection_name]
    except Exception as e:
        logger.error(f"Failed to connect to custom MongoDB for owner {owner_id}: {e}")
        return None


# ── Background Task: Process + embed ──────────────────────────────────────────
def process_file_and_embed(
    file_path: str,
    file_name: str,
    owner_id: str,
    db_entry: dict | None = None       # None → default DB
):
    try:
        logger.info(f"Processing file: {file_name} for owner: {owner_id}")

        if file_name.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)

        for chunk in chunks:
            chunk.metadata['owner_id'] = owner_id
            chunk.metadata['file_name'] = file_name      # <-- used for delete later

        embeddings = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=load_hf_api(),
        )

        # ── Default DB (our own MongoDB Atlas) ────────────────────────────────
        if db_entry is None:
            _embed_mongo(chunks, embeddings, owner_id, file_name, vector_collection)
            return

        provider = db_entry.get('provider')
        config   = db_entry.get('config', {})

        # ── Custom Postgres ───────────────────────────────────────────────────
        if provider == 'postgres':
            try:
                logger.info(f"Using custom Postgres (pgvector) for owner {owner_id}")
                PGVector.from_documents(
                    documents=chunks,
                    embedding=embeddings,
                    collection_name="embeddings",
                    connection=config.get('connection_string'),
                    use_jsonb=True,
                )
                logger.info(f"Embedded {len(chunks)} chunks into Postgres | file: {file_name}")
            except Exception as e:
                logger.error(f"Failed to embed into Postgres for owner {owner_id}: {e}")

        # ── Custom MongoDB ────────────────────────────────────────────────────
        elif provider == 'mongo':
            target = get_mongo_collection_from_entry(db_entry, owner_id)
            if target:
                _embed_mongo(chunks, embeddings, owner_id, file_name, target)
            else:
                logger.error(f"Falling back to default DB for owner {owner_id}")
                _embed_mongo(chunks, embeddings, owner_id, file_name, vector_collection)

        else:
            logger.error(f"Unknown provider '{provider}' — falling back to default DB")
            _embed_mongo(chunks, embeddings, owner_id, file_name, vector_collection)

    except Exception as e:
        logger.error(f"Error processing file {file_name} for owner {owner_id}: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ── Helper: embed into a MongoDB Atlas vector collection ──────────────────────
def _embed_mongo(chunks, embeddings, owner_id, file_name, target_collection):
    try:
        MongoDBAtlasVectorSearch.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection=target_collection,
            index_name="vector_index_qab"
        )
        logger.info(f"Embedded {len(chunks)} chunks into MongoDB | file: {file_name} | owner: {owner_id}")
    except Exception as e:
        logger.error(f"Failed to embed into MongoDB for owner {owner_id}: {e}")


# ── POST /upload ───────────────────────────────────────────────────────────────
@kb_router.post("/upload")
async def upload_document(
    bt: BackgroundTasks,
    file: UploadFile = File(...),
    db_id: str = Query(default=None, description="Custom DB ObjectId, or omit for default DB"),
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Upload request from {current_user['email']} | db_id={db_id}")

    if not file.filename.endswith(('.txt', '.pdf')):
        return error_response(400, message="Only .txt and .pdf files are supported.")

    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(404, message="User not found.")

    db_entry = None  # default DB

    if db_id:
        # Validate db_id format
        try:
            db_object_id = ObjectId(db_id)
        except Exception:
            return error_response(400, message="Invalid db_id format.")

        # Must belong to this user
        db_entry = await db_collection.find_one({
            '_id': db_object_id,
            'owner_id': ObjectId(current_user['_id'])
        })
        if not db_entry:
            return error_response(404, message="DB not found or does not belong to you.")

    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", f"{current_user['_id']}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    bt.add_task(
        process_file_and_embed,
        file_path,
        file.filename,
        str(current_user['_id']),
        db_entry,          # None = default, dict = custom
    )

    logger.info(f"File '{file.filename}' queued | owner: {current_user['email']}")
    return success_response(202, message="File uploaded successfully. Processing in background.")


# ── DELETE /delete-file ────────────────────────────────────────────────────────
@kb_router.delete("/delete-file")
async def delete_file_from_kb(
    file_name: str = Query(..., description="Exact filename e.g. raju_sabji.txt"),
    db_id: str = Query(default=None, description="Custom DB ObjectId, or omit for default DB"),
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Delete KB file request from {current_user['email']} | file: {file_name} | db_id: {db_id}")

    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(404, message="User not found.")

    owner_id = str(current_user['_id'])

    # ── Default DB ─────────────────────────────────────────────────────────────
    if not db_id:
        result = vector_collection.delete_many({
            'metadata.owner_id': owner_id,
            'metadata.file_name': file_name,
        })
        logger.info(f"Deleted {result.deleted_count} chunks from default DB | file: {file_name}")
        return success_response(200, message=f"Deleted {result.deleted_count} chunks for '{file_name}' from default DB.")

    # ── Custom DB ──────────────────────────────────────────────────────────────
    try:
        db_object_id = ObjectId(db_id)
    except Exception:
        return error_response(400, message="Invalid db_id format.")

    db_entry = await db_collection.find_one({
        '_id': db_object_id,
        'owner_id': ObjectId(current_user['_id'])
    })
    if not db_entry:
        return error_response(404, message="DB not found or does not belong to you.")

    provider = db_entry.get('provider')
    config   = db_entry.get('config', {})

    if provider == 'mongo':
        target = get_mongo_collection_from_entry(db_entry, owner_id)
        if not target:
            return error_response(500, message="Could not connect to custom MongoDB.")

        result = target.delete_many({
            'metadata.owner_id': owner_id,
            'metadata.file_name': file_name,
        })
        logger.info(f"Deleted {result.deleted_count} chunks from custom MongoDB | file: {file_name}")
        return success_response(200, message=f"Deleted {result.deleted_count} chunks for '{file_name}' from custom MongoDB.")

    elif provider == 'postgres':
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(config.get('connection_string'))
            with engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM langchain_pg_embedding
                    WHERE cmetadata->>'owner_id' = :owner_id
                    AND cmetadata->>'file_name' = :file_name
                """), {"owner_id": owner_id, "file_name": file_name})
                conn.commit()
            logger.info(f"Deleted {result.rowcount} chunks from Postgres | file: {file_name}")
            return success_response(200, message=f"Deleted {result.rowcount} chunks for '{file_name}' from Postgres.")
        except Exception as e:
            logger.error(f"Failed to delete from Postgres for owner {owner_id}: {e}")
            return error_response(500, message="Failed to delete from Postgres.")

    return error_response(400, message=f"Unsupported provider '{provider}'.")



# ── GET /files ─────────────────────────────────────────────────────────────────
@kb_router.get("/files")
async def get_knowledge_base_files(current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching KB files for {current_user['email']}")

    user_data = await users_collection.find_one({'_id': ObjectId(current_user['_id'])})
    if not user_data:
        return error_response(404, message="User not found.")

    owner_id = str(current_user['_id'])
    all_files = []

    # ── 1. Default MongoDB Atlas ───────────────────────────────────────────────
    try:
        default_files = vector_collection.aggregate([
            {'$match': {'metadata.owner_id': owner_id}},
            {'$group': {
                '_id': '$metadata.file_name',
                'chunk_count': {'$sum': 1}
            }}
        ])
        for f in default_files:
            all_files.append({
                'file_name':   f['_id'],
                'db_id':       'default',
                'db_name':     'Default DB',
                'provider':    'MongoDB',
                'chunk_count': f['chunk_count'],
            })
    except Exception as e:
        logger.error(f"Failed to fetch files from default DB for owner {owner_id}: {e}")

    # ── 2. Custom DBs ──────────────────────────────────────────────────────────
    db_ids = user_data.get('custom_db', [])

    async for db_entry in db_collection.find({'_id': {'$in': db_ids}}):
        provider = db_entry.get('provider')
        config   = db_entry.get('config', {})
        db_id    = str(db_entry['_id'])
        db_name  = db_entry.get('name', 'Unnamed DB')

        # ── Custom MongoDB ─────────────────────────────────────────────────────
        if provider == 'mongo':
            try:
                target = get_mongo_collection_from_entry(db_entry, owner_id)
                if not target:
                    raise Exception("Could not get collection")

                cursor = target.aggregate([
                    {'$match': {'metadata.owner_id': owner_id}},
                    {'$group': {
                        '_id': '$metadata.file_name',
                        'chunk_count': {'$sum': 1}
                    }}
                ])
                for f in cursor:
                    all_files.append({
                        'file_name':   f['_id'],
                        'db_id':       db_id,
                        'db_name':     db_name,
                        'provider':    'MongoDB',
                        'chunk_count': f['chunk_count'],
                    })
            except Exception as e:
                logger.error(f"Failed to fetch files from custom MongoDB {db_id}: {e}")

        # ── Custom Postgres ────────────────────────────────────────────────────
        elif provider == 'postgres':
            try:
                from sqlalchemy import create_engine, text
                engine = create_engine(config.get('connection_string'))
                with engine.connect() as conn:
                    rows = conn.execute(text("""
                        SELECT
                            cmetadata->>'file_name' AS file_name,
                            COUNT(*)                AS chunk_count
                        FROM langchain_pg_embedding
                        WHERE cmetadata->>'owner_id' = :owner_id
                        GROUP BY cmetadata->>'file_name'
                    """), {"owner_id": owner_id}).fetchall()

                for row in rows:
                    all_files.append({
                        'file_name':   row.file_name,
                        'db_id':       db_id,
                        'db_name':     db_name,
                        'provider':    'postgres',
                        'chunk_count': row.chunk_count,
                    })
            except Exception as e:
                logger.error(f"Failed to fetch files from Postgres {db_id}: {e}")

    logger.info(f"Found {len(all_files)} files across all DBs for owner {owner_id}")
    return success_response(200, message="Knowledge base files fetched.", data=all_files)












