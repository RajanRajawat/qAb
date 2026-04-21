from fastapi import APIRouter, File, UploadFile, Depends, BackgroundTasks
from database.db import users_collection, vector_collection, db_collection, kb_collection, agents_collection
from database.models import CreateKnowledgeBase, UpdateKnowledgeBase, KnowledgeBaseVectorSearchRequest
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
from pymongo import ReturnDocument
import os
import shutil
import datetime


kb_router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


#- Embeddings
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

EMBEDDING_MODEL_OPTIONS = {
    "sentence-transformers/all-MiniLM-L6-v2": {
        "label": "All MiniLM L6 v2",
        "provider": "sentence-transformers",
        "description": "Balanced general-purpose embeddings with 384 dimensions.",
    },
    "sentence-transformers/paraphrase-MiniLM-L3-v2": {
        "label": "Paraphrase MiniLM L3 v2",
        "provider": "sentence-transformers",
        "description": "Lighter 384-dimensional embeddings tuned for semantic similarity.",
    },
}


def serialize_embedding_options():
    options = []

    for model_name, meta in EMBEDDING_MODEL_OPTIONS.items():
        options.append({
            "value": model_name,
            "label": meta["label"],
            "provider": meta["provider"],
            "description": meta["description"],
            "is_default": model_name == DEFAULT_EMBEDDING_MODEL,
        })

    return options


def resolve_embedding_model_name(model_name: str | None):
    if model_name in EMBEDDING_MODEL_OPTIONS:
        return model_name
    return DEFAULT_EMBEDDING_MODEL


def get_embedding_client(model_name: str | None):
    resolved_model_name = resolve_embedding_model_name(model_name)

    return HuggingFaceEndpointEmbeddings(
        model=resolved_model_name,
        huggingfacehub_api_token=load_hf_api(),
    )


def get_embedding_model_label(model_name: str | None):
    resolved_model_name = resolve_embedding_model_name(model_name)
    return EMBEDDING_MODEL_OPTIONS[resolved_model_name]["label"]


#- Helpers
def serialize_kb(kb: dict):
    embedding_model = resolve_embedding_model_name(kb.get("embedding_model"))

    return {
        "kb_id": str(kb["_id"]),
        "name": kb.get("name"),
        "owner_id": str(kb.get("owner_id")),
        "db_id": kb.get("db_id"),
        "db_name": kb.get("db_name"),
        "files": kb.get("files", []),
        "file_count": len(kb.get("files", [])),
        "embedding_model": embedding_model,
        "embedding_label": get_embedding_model_label(embedding_model),
        "created_at": str(kb.get("created_at")),
        "updated_at": str(kb.get("updated_at")) if kb.get("updated_at") else None,
    }


async def get_user_data(current_user: dict):
    return await users_collection.find_one({"_id": ObjectId(current_user["_id"])})


async def get_user_db_entry(owner_id: str, db_id: str | None):
    if not db_id or db_id == "default":
        return None

    try:
        db_object_id = ObjectId(db_id)
    except Exception:
        return "invalid"

    return await db_collection.find_one({
        "_id": db_object_id,
        "owner_id": ObjectId(owner_id)
    })


async def get_kb_entry(kb_id: str, owner_id: str):
    try:
        kb_object_id = ObjectId(kb_id)
    except Exception:
        return None

    return await kb_collection.find_one({
        "_id": kb_object_id,
        "owner_id": ObjectId(owner_id)
    })


def get_db_name(db_entry: dict | None):
    if not db_entry:
        return "Default DB"
    return db_entry.get("name", "Custom DB")


def get_mongo_collection_from_entry(db_entry: dict):
    config = db_entry.get("config", {})

    try:
        client = MongoClient(config.get("connection_string"))
        return client[config.get("db_name")][config.get("collection_name")]
    except Exception as e:
        logger.error(f"Could not connect to custom MongoDB: {e}")
        return None


async def delete_kb_reference_from_agents(kb_id: str, owner_id: str):
    await agents_collection.update_many(
        {
            "owner_id": ObjectId(owner_id),
            "knowledge_base_id": kb_id
        },
        {
            "$set": {
                "knowledge_base": False,
                "knowledge_base_id": None,
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        }
    )


def delete_embeddings_from_default(owner_id: str, kb_id: str, file_name: str | None = None):
    query = {
        "owner_id": owner_id,
        "knowledge_base_id": kb_id,
    }
    if file_name:
        query["file_name"] = file_name
    result = vector_collection.delete_many(query)
    return result.deleted_count


def delete_embeddings_from_custom_mongo(db_entry: dict, owner_id: str, kb_id: str, file_name: str | None = None):
    target_collection = get_mongo_collection_from_entry(db_entry)
    if target_collection is None:
        return None

    query = {
        "owner_id": owner_id,
        "knowledge_base_id": kb_id,
    }
    if file_name:
        query["file_name"] = file_name

    result = target_collection.delete_many(query)
    return result.deleted_count


def delete_embeddings_from_postgres(db_entry: dict, owner_id: str, kb_id: str, file_name: str | None = None):
    try:
        from sqlalchemy import create_engine, text
        connection_string = db_entry["config"]["connection_string"].replace("postgres://", "postgresql://")
        engine = create_engine(connection_string)

        sql = """
            DELETE FROM langchain_pg_embedding
            WHERE cmetadata->>'owner_id' = :owner_id
            AND cmetadata->>'knowledge_base_id' = :kb_id
        """
        params = {"owner_id": owner_id, "kb_id": kb_id}

        if file_name:
            sql += " AND cmetadata->>'file_name' = :file_name"
            params["file_name"] = file_name

        logger.info(f"Attempting Postgres deletion: {kb_id} for owner {owner_id}")

        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()
            logger.info(f"Postgres deletion successful. Rows affected: {result.rowcount}")

        return result.rowcount
    except Exception as e:
        logger.error(f"Could not delete embeddings from Postgres: {e}")
        return 0


def delete_embeddings_for_kb(owner_id: str, kb_id: str, db_entry: dict | None, file_name: str | None = None):
    if not db_entry:
        return delete_embeddings_from_default(owner_id, kb_id, file_name)

    provider = db_entry.get("provider")

    if provider == "mongo":
        return delete_embeddings_from_custom_mongo(db_entry, owner_id, kb_id, file_name)

    if provider == "postgres":
        return delete_embeddings_from_postgres(db_entry, owner_id, kb_id, file_name)

    return None


def delete_all_embeddings_for_custom_db(owner_id: str, db_entry: dict):
    provider = db_entry.get("provider")

    if provider == "mongo":
        target_collection = get_mongo_collection_from_entry(db_entry)
        if target_collection is None:
            return None
        result = target_collection.delete_many({
            "owner_id": owner_id
        })
        return result.deleted_count

    if provider == "postgres":
        try:
            from sqlalchemy import create_engine, text
            connection_string = db_entry["config"]["connection_string"].replace("postgres://", "postgresql://")
            engine = create_engine(connection_string)
            sql = "DELETE FROM langchain_pg_embedding WHERE cmetadata->>'owner_id' = :owner_id"

            logger.info(f"Attempting full Postgres cleanup for owner {owner_id}")
            with engine.connect() as conn:
                result = conn.execute(text(sql), {"owner_id": owner_id})
                conn.commit()
                logger.info(f"Postgres full cleanup successful. Rows affected: {result.rowcount}")
            return result.rowcount
        except Exception as e:
            logger.error(f"Could not delete all embeddings from Postgres: {e}")
            return 0

    return None


async def cleanup_kbs_for_custom_db(owner_id: str, db_id: str):
    deleted_files = 0
    deleted_kbs = 0

    async for kb in kb_collection.find({
        "owner_id": ObjectId(owner_id),
        "db_id": db_id
    }):
        deleted_files += len(kb.get("files", []))
        await delete_kb_reference_from_agents(str(kb["_id"]), owner_id)
        await kb_collection.delete_one({"_id": kb["_id"]})
        deleted_kbs += 1

    return {
        "deleted_kbs": deleted_kbs,
        "deleted_files": deleted_files,
    }


def process_file_and_embed(file_path: str, file_name: str, owner_id: str, kb_id: str, embedding_model: str, db_entry: dict | None = None):
    try:
        logger.info(f"Processing file {file_name} for kb {kb_id}")

        if file_name.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            documents = loader.load()
        else:
            encodings = ["utf-8", "latin-1", "cp1252"]
            documents = None

            for encoding in encodings:
                try:
                    loader = TextLoader(file_path, encoding=encoding)
                    documents = loader.load()
                    logger.info(f"Successfully loaded {file_name} with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue

            if documents is None:
                raise ValueError(f"Could not decode file {file_name} with supported encodings.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(documents)

        for chunk in chunks:
            chunk.metadata["owner_id"] = owner_id
            chunk.metadata["file_name"] = file_name
            chunk.metadata["knowledge_base_id"] = kb_id
            chunk.metadata["embedding_model"] = resolve_embedding_model_name(embedding_model)

        embeddings = get_embedding_client(embedding_model)

        if not db_entry:
            logger.info(f"Embedding {len(chunks)} chunks into default MongoDB collection for kb {kb_id}")
            MongoDBAtlasVectorSearch.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection=vector_collection,
                index_name="vector_index_qab"
            )
            logger.info(f"Successfully embedded chunks for kb {kb_id} into default store")
            return

        if db_entry.get("provider") == "mongo":
            target_collection = get_mongo_collection_from_entry(db_entry)
            if target_collection is None:
                raise ValueError("Could not connect to custom MongoDB.")

            logger.info(f"Embedding {len(chunks)} chunks into custom MongoDB for kb {kb_id}")
            MongoDBAtlasVectorSearch.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection=target_collection,
                index_name="vector_index_qab"
            )
            logger.info(f"Successfully embedded chunks for kb {kb_id} into custom MongoDB")
            return

        if db_entry.get("provider") == "postgres":
            logger.info(f"Embedding {len(chunks)} chunks into custom Postgres for kb {kb_id}")
            PGVector.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection_name="embeddings",
                connection=db_entry["config"]["connection_string"],
                use_jsonb=True,
            )
            logger.info(f"Successfully embedded chunks for kb {kb_id} into custom Postgres")
            return

        raise ValueError("Unsupported DB provider.")

    except Exception as e:
        logger.error(f"File embedding failed for kb {kb_id}: {str(e)}")
        try:
            from database.db import vec_db
            sync_kb_collection = vec_db["kb"]
            sync_kb_collection.update_one(
                {"_id": ObjectId(kb_id)},
                {"$pull": {"files": file_name}}
            )
            logger.info(f"Removed {file_name} from kb {kb_id} due to embedding failure")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup KB entry after embedding failure: {cleanup_error}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def search_kb_chunks(query: str, owner_id: str, kb_entry: dict, db_entry: dict | None = None, limit: int = 3):
    kb_id = str(kb_entry["_id"])
    embedding_model = resolve_embedding_model_name(kb_entry.get("embedding_model"))

    try:
        embeddings = get_embedding_client(embedding_model)

        if db_entry and db_entry.get("provider") == "postgres":
            logger.info(f"Vector search: using custom Postgres for kb {kb_id}")
            vector_store = PGVector(
                embeddings=embeddings,
                collection_name="embeddings",
                connection=db_entry["config"]["connection_string"],
                use_jsonb=True,
            )
            return vector_store.similarity_search_with_score(
                query,
                k=limit,
                filter={
                    "owner_id": owner_id,
                    "knowledge_base_id": kb_id,
                }
            )

        target_collection = None
        if db_entry and db_entry.get("provider") == "mongo":
            target_collection = get_mongo_collection_from_entry(db_entry)
            logger.info(f"Vector search: using custom MongoDB for kb {kb_id}")

        if target_collection is None:
            target_collection = vector_collection
            logger.info(f"Vector search: using default vector collection for kb {kb_id}")

        doc_count = target_collection.count_documents({
            "owner_id": owner_id,
            "knowledge_base_id": kb_id,
        })

        if doc_count == 0:
            logger.info(f"Vector search: no documents found for kb {kb_id}")
            return []

        vector_store = MongoDBAtlasVectorSearch(
            collection=target_collection,
            embedding=embeddings,
            index_name="vector_index_qab"
        )

        return vector_store.similarity_search_with_score(
            query,
            k=limit,
            pre_filter={
                "owner_id": {"$eq": owner_id},
                "knowledge_base_id": {"$eq": kb_id},
            }
        )
    except Exception as e:
        logger.error(f"Vector search failed for kb {kb_id}: {str(e)}")
        return []


def serialize_search_results(results: list):
    serialized_results = []

    for item in results:
        doc = item[0]
        score = item[1] if len(item) > 1 else None

        serialized_results.append({
            "content": doc.page_content,
            "score": float(score) if score is not None else None,
            "metadata": {
                "file_name": doc.metadata.get("file_name"),
                "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
                "embedding_model": resolve_embedding_model_name(doc.metadata.get("embedding_model")),
            }
        })

    return serialized_results


#- Routes
@kb_router.get("/embedding-options")
async def get_embedding_options(current_user: dict = Depends(get_current_user)):
    logger.info(f"Embedding options requested by {current_user['email']}")

    return success_response(
        200,
        message="Embedding options fetched successfully.",
        data=serialize_embedding_options()
    )


@kb_router.post("/create")
async def create_knowledge_base(payload: CreateKnowledgeBase, current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base create request from {current_user['email']}")

    user_data = await get_user_data(current_user)
    if not user_data:
        return error_response(404, message="User not found.")

    if payload.embedding_model not in EMBEDDING_MODEL_OPTIONS:
        return error_response(400, message="Unsupported embedding model selected.")

    db_entry = await get_user_db_entry(current_user["_id"], payload.db_id)
    if db_entry == "invalid":
        return error_response(400, message="Invalid db_id format.")
    if payload.db_id and payload.db_id != "default" and not db_entry:
        return error_response(404, message="DB not found or does not belong to you.")

    kb_data = {
        "name": payload.name,
        "owner_id": ObjectId(current_user["_id"]),
        "files": [],
        "db_id": str(db_entry["_id"]) if db_entry else "default",
        "db_name": get_db_name(db_entry),
        "embedding_model": resolve_embedding_model_name(payload.embedding_model),
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    }

    created_kb = await kb_collection.insert_one(kb_data)
    kb_data["_id"] = created_kb.inserted_id

    return success_response(
        201,
        message="Knowledge base created successfully.",
        data=serialize_kb(kb_data)
    )


@kb_router.get("/all")
async def get_all_knowledge_bases(current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base list request from {current_user['email']}")

    kbs = []
    async for kb in kb_collection.find({"owner_id": ObjectId(current_user["_id"])}).sort("created_at", -1):
        kbs.append(serialize_kb(kb))

    return success_response(200, message="Knowledge bases fetched successfully.", data=kbs)


@kb_router.get("/{kb_id}")
async def get_knowledge_base(kb_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base detail request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    return success_response(200, message="Knowledge base fetched successfully.", data=serialize_kb(kb_entry))


@kb_router.patch("/update/{kb_id}")
async def update_knowledge_base(kb_id: str, payload: UpdateKnowledgeBase, current_user: dict = Depends(get_current_user)):
    logger.info(f"Knowledge base update request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    updated_kb = await kb_collection.find_one_and_update(
        {
            "_id": kb_entry["_id"],
            "owner_id": ObjectId(current_user["_id"])
        },
        {
            "$set": {
                "name": payload.name,
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        },
        return_document=ReturnDocument.AFTER
    )

    return success_response(200, message="Knowledge base updated successfully.", data=serialize_kb(updated_kb))


@kb_router.post("/add-file/{kb_id}")
async def add_file_to_knowledge_base(
    kb_id: str,
    bt: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Add file request for kb {kb_id} from {current_user['email']}")

    if not file.filename.endswith((".txt", ".pdf")):
        return error_response(400, message="Only .txt and .pdf files are supported.")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    if file.filename in kb_entry.get("files", []):
        return error_response(400, message="This file already exists in the knowledge base.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", f"{current_user['_id']}_{kb_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    await kb_collection.update_one(
        {"_id": kb_entry["_id"]},
        {
            "$push": {"files": file.filename},
            "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc)}
        }
    )

    bt.add_task(
        process_file_and_embed,
        file_path,
        file.filename,
        str(current_user["_id"]),
        kb_id,
        resolve_embedding_model_name(kb_entry.get("embedding_model")),
        db_entry,
    )

    return success_response(202, message="File added successfully. Processing started.")


@kb_router.delete("/remove-file/{kb_id}")
async def remove_file_from_knowledge_base(
    kb_id: str,
    file_name: str,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Remove file request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    if file_name not in kb_entry.get("files", []):
        return error_response(404, message="File not found in this knowledge base.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    deleted_count = delete_embeddings_for_kb(str(current_user["_id"]), kb_id, db_entry, file_name)

    if deleted_count is None:
        return error_response(500, message="Could not remove file embeddings.")

    await kb_collection.update_one(
        {"_id": kb_entry["_id"]},
        {
            "$pull": {"files": file_name},
            "$set": {"updated_at": datetime.datetime.now(datetime.timezone.utc)}
        }
    )

    return success_response(
        200,
        message=f"File removed successfully. Deleted {deleted_count} embeddings."
    )


@kb_router.post("/test-search/{kb_id}")
async def test_knowledge_base_search(
    kb_id: str,
    payload: KnowledgeBaseVectorSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Knowledge base vector search test requested for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    results = search_kb_chunks(
        payload.query,
        str(current_user["_id"]),
        kb_entry,
        db_entry,
        payload.limit
    )

    return success_response(
        200,
        message="Knowledge base search completed successfully.",
        data={
            "kb": serialize_kb(kb_entry),
            "query": payload.query,
            "limit": payload.limit,
            "results": serialize_search_results(results)
        }
    )


@kb_router.delete("/delete/{kb_id}")
async def delete_knowledge_base(kb_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Delete knowledge base request for kb {kb_id} from {current_user['email']}")

    kb_entry = await get_kb_entry(kb_id, current_user["_id"])
    if not kb_entry:
        return error_response(404, message="Knowledge base not found.")

    db_entry = await get_user_db_entry(current_user["_id"], kb_entry.get("db_id"))
    if kb_entry.get("db_id") != "default" and not db_entry:
        return error_response(404, message="Linked DB not found for this knowledge base.")

    deleted_count = delete_embeddings_for_kb(str(current_user["_id"]), kb_id, db_entry)

    if deleted_count is None:
        return error_response(500, message="Could not delete knowledge base embeddings.")

    await delete_kb_reference_from_agents(kb_id, current_user["_id"])
    await kb_collection.delete_one({"_id": kb_entry["_id"]})

    return success_response(
        200,
        message=f"Knowledge base deleted successfully. Deleted {deleted_count} embeddings."
    )
