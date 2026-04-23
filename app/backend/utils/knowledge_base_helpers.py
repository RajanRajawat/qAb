import datetime
import os
from bson import ObjectId
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymongo import MongoClient
from database.db import agents_collection, db_collection, kb_collection, users_collection, vector_collection
from utils.env_loaders import load_hf_api
from utils.general import ensure_object_id, object_id_match
from utils.loggers import logger

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
        huggingfacehub_api_token=load_hf_api,
    )

def get_embedding_model_label(model_name: str | None):
    resolved_model_name = resolve_embedding_model_name(model_name)
    return EMBEDDING_MODEL_OPTIONS[resolved_model_name]["label"]

def serialize_kb(kb: dict):
    embedding_model = resolve_embedding_model_name(kb.get("embedding_model"))
    db_id = kb.get("db_id")
    serialized_db_id = str(db_id) if db_id != "default" and db_id is not None else db_id

    return {
        "kb_id": str(kb["_id"]),
        "name": kb.get("name"),
        "owner_id": str(kb.get("owner_id")),
        "db_id": serialized_db_id,
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
        db_object_id = ensure_object_id(db_id)
    except Exception:
        return "invalid"

    return await db_collection.find_one({
        "_id": db_object_id,
        "owner_id": ObjectId(owner_id),
    })


async def get_kb_entry(kb_id: str, owner_id: str):
    try:
        kb_object_id = ObjectId(kb_id)
    except Exception:
        return None

    return await kb_collection.find_one({
        "_id": kb_object_id,
        "owner_id": ObjectId(owner_id),
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
            "knowledge_base_id": object_id_match(kb_id),
        },
        {
            "$set": {
                "knowledge_base": False,
                "knowledge_base_id": None,
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        },
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
            "owner_id": owner_id,
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
    db_filter = object_id_match(db_id)
    deleted_files = 0
    deleted_kbs = 0

    async for kb in kb_collection.find({
        "owner_id": ObjectId(owner_id),
        "db_id": db_filter,
    }):
        deleted_files += len(kb.get("files", []))
        await delete_kb_reference_from_agents(kb["_id"], owner_id)
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
                index_name="vector_index",
            )
            return

        provider = db_entry.get("provider")

        if provider == "mongo":
            target_collection = get_mongo_collection_from_entry(db_entry)
            if target_collection is None:
                raise ValueError("Could not connect to linked MongoDB.")

            logger.info(f"Embedding {len(chunks)} chunks into custom MongoDB for kb {kb_id}")
            MongoDBAtlasVectorSearch.from_documents(
                documents=chunks,
                embedding=embeddings,
                collection=target_collection,
                index_name="vector_index",
            )
            return

        if provider == "postgres":
            connection_string = db_entry["config"]["connection_string"].replace("postgres://", "postgresql://")
            logger.info(f"Embedding {len(chunks)} chunks into PostgreSQL for kb {kb_id}")
            PGVector.from_documents(
                embedding=embeddings,
                documents=chunks,
                collection_name="langchain_pg_embedding",
                connection=connection_string,
                use_jsonb=True,
            )
            return

        raise ValueError(f"Unsupported DB provider: {provider}")

    except Exception as e:
        logger.error(f"Embedding task failed for {file_name}: {str(e)}")
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


def search_kb_chunks(query: str, owner_id: str, kb_entry: dict, db_entry: dict | None = None, limit: int = 3):
    kb_id = str(kb_entry["_id"])
    embedding_model = resolve_embedding_model_name(kb_entry.get("embedding_model"))
    embeddings = get_embedding_client(embedding_model)

    if not db_entry:
        vector_store = MongoDBAtlasVectorSearch(
            collection=vector_collection,
            embedding=embeddings,
            index_name="vector_index",
        )
        return vector_store.similarity_search_with_score(
            query=query,
            k=limit,
            pre_filter={
                "owner_id": owner_id,
                "knowledge_base_id": kb_id,
            },
        )

    provider = db_entry.get("provider")

    if provider == "mongo":
        target_collection = get_mongo_collection_from_entry(db_entry)
        if target_collection is None:
            raise ValueError("Could not connect to linked MongoDB.")

        vector_store = MongoDBAtlasVectorSearch(
            collection=target_collection,
            embedding=embeddings,
            index_name="vector_index",
        )
        return vector_store.similarity_search_with_score(
            query=query,
            k=limit,
            pre_filter={
                "owner_id": owner_id,
                "knowledge_base_id": kb_id,
            },
        )

    if provider == "postgres":
        connection_string = db_entry["config"]["connection_string"].replace("postgres://", "postgresql://")
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name="langchain_pg_embedding",
            connection=connection_string,
            use_jsonb=True,
        )
        return vector_store.similarity_search_with_score(
            query=query,
            k=limit,
            filter={
                "owner_id": {"$eq": owner_id},
                "knowledge_base_id": {"$eq": kb_id},
            },
        )

    raise ValueError(f"Unsupported DB provider: {provider}")


def serialize_search_results(results: list):
    serialized = []

    for doc, score in results:
        serialized.append({
            "content": doc.page_content,
            "score": score,
            "metadata": {
                "file_name": doc.metadata.get("file_name"),
                "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
                "embedding_model": doc.metadata.get("embedding_model"),
            },
        })

    return serialized
