import datetime, ast, json, psycopg2
from collections.abc import Mapping
from bson import ObjectId
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri
from database.db import agents_collection, data_query_collection, db_collection, users_collection
from utils.general import ensure_object_id, object_id_match


POSTGRES_INTERNAL_TABLES = {"langchain_pg_collection", "langchain_pg_embedding"}


def normalize_postgres_uri(uri: str) -> str:
    if "://" in uri:
        scheme, rest = uri.split("://", 1)
        if "+" in scheme:
            return f"{scheme.split('+')[0]}://{rest}"
    return uri


def serialize_json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): serialize_json_safe(item) for key, item in value.items()}
    return value


def strip_code_fences(value: str) -> str:
    text = value.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return text


def parse_mongo_query_payload(query: str):
    cleaned_query = strip_code_fences(query)

    try:
        return json.loads(cleaned_query)
    except json.JSONDecodeError:
        pass

    try:
        parsed = ast.literal_eval(cleaned_query)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(
            "Mongo query must be valid JSON. Example: "
            '{"operation":"find","filter":{},"projection":{"field":1},"limit":20}'
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError("Mongo query must resolve to a JSON object.")

    return parsed


def serialize_data_query(data_query: dict):
    db_id = data_query.get("db_id")
    return {
        "data_query_id": str(data_query["_id"]),
        "name": data_query.get("name"),
        "owner_id": str(data_query.get("owner_id")),
        "db_id": str(db_id) if db_id is not None else None,
        "db_name": data_query.get("db_name"),
        "provider": data_query.get("provider"),
        "sources": data_query.get("sources", []),
        "created_at": str(data_query.get("created_at")),
        "updated_at": str(data_query.get("updated_at")) if data_query.get("updated_at") else None,
    }


async def get_owned_db_entry(owner_id: str, db_id: str):
    try:
        db_object_id = ensure_object_id(db_id)
    except Exception:
        return None

    return await db_collection.find_one({
        "_id": db_object_id,
        "owner_id": ObjectId(owner_id),
    })


async def get_owned_data_query(owner_id: str, data_query_id: str):
    try:
        dq_object_id = ensure_object_id(data_query_id)
    except Exception:
        return None

    return await data_query_collection.find_one({
        "_id": dq_object_id,
        "owner_id": ObjectId(owner_id),
    })


def get_mongo_source_database_name(db_entry: dict) -> str | None:
    config = db_entry.get("config", {})
    if config.get("query_db_name"):
        return config["query_db_name"]

    try:
        parsed = parse_uri(config.get("connection_string"))
    except Exception:
        parsed = {}

    return parsed.get("database")


def get_mongo_source_database(db_entry: dict):
    config = db_entry.get("config", {})
    database_name = get_mongo_source_database_name(db_entry)
    if not database_name:
        raise ValueError("MongoDB connection URI must include a database name to use Data Query.")

    client = MongoClient(config.get("connection_string"))
    return client[database_name]


def infer_mongo_columns(sample_docs: list[dict]):
    fields: dict[str, str] = {}

    for doc in sample_docs:
        for key, value in doc.items():
            if key not in fields:
                fields[key] = type(value).__name__

    return [
        {
            "name": key,
            "data_type": value,
            "description": "",
        }
        for key, value in sorted(fields.items())
    ]


def inspect_mongo_sources(db_entry: dict):
    source_db = get_mongo_source_database(db_entry)
    excluded = {db_entry.get("config", {}).get("collection_name")} if db_entry.get("config", {}).get("collection_name") else set()
    sources = []

    for collection_name in sorted(source_db.list_collection_names()):
        if collection_name in excluded:
            continue

        collection = source_db[collection_name]
        preview = [serialize_json_safe(item) for item in collection.find({}, limit=3)]
        sources.append({
            "name": collection_name,
            "source_type": "collection",
            "column_count": len(infer_mongo_columns(preview)),
            "columns": infer_mongo_columns(preview),
            "preview_rows": preview,
        })

    return {
        "db_name": source_db.name,
        "sources": sources,
    }


def inspect_postgres_sources(db_entry: dict):
    connection_uri = normalize_postgres_uri(db_entry["config"]["connection_string"])
    sources = []

    with psycopg2.connect(connection_uri) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            tables = [row["table_name"] for row in cur.fetchall() if row["table_name"] not in POSTGRES_INTERNAL_TABLES]

            for table_name in tables:
                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table_name,),
                )
                columns = [
                    {
                        "name": row["column_name"],
                        "data_type": row["data_type"],
                        "description": "",
                    }
                    for row in cur.fetchall()
                ]

                preview_query = sql.SQL("SELECT * FROM {} LIMIT 3").format(sql.Identifier(table_name))
                cur.execute(preview_query)
                preview = [serialize_json_safe(dict(row)) for row in cur.fetchall()]

                sources.append({
                    "name": table_name,
                    "source_type": "table",
                    "column_count": len(columns),
                    "columns": columns,
                    "preview_rows": preview,
                })

    return {
        "db_name": db_entry.get("name"),
        "sources": sources,
    }


def inspect_database_sources(db_entry: dict):
    provider = db_entry.get("provider")
    if provider == "mongo":
        return inspect_mongo_sources(db_entry)
    if provider == "postgres":
        return inspect_postgres_sources(db_entry)
    raise ValueError("Unsupported database provider.")


def validate_selected_sources(db_entry: dict, selected_sources: list[dict]):
    inspection = inspect_database_sources(db_entry)
    available = {source["name"]: source for source in inspection["sources"]}

    for source in selected_sources:
        available_source = available.get(source["name"])
        if not available_source:
            raise ValueError(f"Source '{source['name']}' was not found in the linked database.")

        available_columns = {column["name"] for column in available_source.get("columns", [])}
        for column in source.get("columns", []):
            if column["name"] not in available_columns:
                raise ValueError(f"Column '{column['name']}' was not found in source '{source['name']}'.")


async def remove_data_query_reference_from_agents(data_query_id: str, owner_id: str):
    await agents_collection.update_many(
        {
            "owner_id": ObjectId(owner_id),
            "data_query_id": object_id_match(data_query_id),
        },
        {
            "$set": {
                "data_query": False,
                "data_query_id": None,
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        },
    )


async def cleanup_data_queries_for_custom_db(owner_id: str, db_id: str):
    db_filter = object_id_match(db_id)
    deleted_data_queries = 0
    removed_ids = []

    async for data_query in data_query_collection.find({
        "owner_id": ObjectId(owner_id),
        "db_id": db_filter,
    }):
        await remove_data_query_reference_from_agents(data_query["_id"], owner_id)
        await data_query_collection.delete_one({"_id": data_query["_id"]})
        deleted_data_queries += 1
        removed_ids.append(data_query["_id"])

    if removed_ids:
        await users_collection.update_one(
            {"_id": ObjectId(owner_id)},
            {"$pull": {"data_queries": {"$in": removed_ids}}},
        )

    return {
        "deleted_data_queries": deleted_data_queries,
    }


def build_data_query_schema_text(data_query: dict):
    lines = [
        f"Data Query: {data_query.get('name')}",
        f"Database: {data_query.get('db_name')} ({data_query.get('provider')})",
        "Allowed sources:",
    ]

    for source in data_query.get("sources", []):
        lines.append(f"- {source['source_type']}: {source['name']}")
        if source.get("description"):
            lines.append(f"  Description: {source['description']}")
        for column in source.get("columns", []):
            column_line = f"  Column: {column['name']}"
            if column.get("data_type"):
                column_line += f" ({column['data_type']})"
            if column.get("description"):
                column_line += f" - {column['description']}"
            lines.append(column_line)

    return "\n".join(lines)


def ensure_postgres_read_only_query(query: str, allowed_sources: set[str]):
    normalized = query.strip().lower()
    if not normalized.startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed.")

    banned_tokens = [" insert ", " update ", " delete ", " drop ", " alter ", " truncate ", " create ", " grant ", " revoke "]
    padded = f" {normalized} "
    if any(token in padded for token in banned_tokens):
        raise ValueError("Only read-only SQL queries are allowed.")

    lowered_allowed = {name.lower() for name in allowed_sources}
    referenced = set()
    tokens = normalized.replace(",", " ").split()
    for index, token in enumerate(tokens[:-1]):
        if token in {"from", "join"}:
            referenced.add(tokens[index + 1].strip('"'))

    if not referenced:
        raise ValueError("Query must reference one of the configured tables.")

    if not referenced.issubset(lowered_allowed):
        raise ValueError("Query references tables outside the configured Data Query scope.")


def execute_postgres_data_query(db_entry: dict, source_name: str, query: str):
    allowed_sources = {source_name}
    ensure_postgres_read_only_query(query, allowed_sources)

    connection_uri = normalize_postgres_uri(db_entry["config"]["connection_string"])
    with psycopg2.connect(connection_uri) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchmany(50)
            return [serialize_json_safe(dict(row)) for row in rows]


def execute_mongo_data_query(db_entry: dict, source_name: str, query: str):
    source_db = get_mongo_source_database(db_entry)
    collection = source_db[source_name]
    payload = parse_mongo_query_payload(query)

    operation = payload.get("operation", "find")
    if operation == "find":
        cursor = collection.find(
            payload.get("filter", {}),
            payload.get("projection"),
            limit=min(int(payload.get("limit", 20)), 50),
        )
        return [serialize_json_safe(item) for item in cursor]

    if operation == "aggregate":
        pipeline = payload.get("pipeline", [])
        for stage in pipeline:
            if "$out" in stage or "$merge" in stage:
                raise ValueError("Aggregate pipeline must be read-only.")
        return [serialize_json_safe(item) for item in collection.aggregate(pipeline)]

    raise ValueError("Unsupported Mongo operation. Use 'find' or 'aggregate'.")


def execute_data_query_source(data_query: dict, db_entry: dict, source_name: str, query: str):
    allowed_sources = {source["name"] for source in data_query.get("sources", [])}
    if source_name not in allowed_sources:
        raise ValueError("Requested source is not part of this Data Query.")

    provider = data_query.get("provider")
    if provider == "postgres":
        return execute_postgres_data_query(db_entry, source_name, query)
    if provider == "mongo":
        return execute_mongo_data_query(db_entry, source_name, query)
    raise ValueError("Unsupported database provider.")

