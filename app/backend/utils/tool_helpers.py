import base64
import datetime
import os
from urllib.parse import urlencode

import jwt
import requests
from bson import ObjectId
from database.db import agents_collection, tools_collection
from utils.env_loaders import load_jwt_secret_key
from utils.general import ensure_object_id
from utils.loggers import logger


WEB_SEARCH_TOOL_KEY = "web_search"
GMAIL_TOOL_KEY = "gmail"

GMAIL_CAPABILITIES = [
    "GMAIL_FETCH_EMAILS",
    "GMAIL_REPLY_TO_THREAD",
    "GMAIL_SEND_EMAIL",
]

TOOL_DEFINITIONS = {
    WEB_SEARCH_TOOL_KEY: {
        "key": WEB_SEARCH_TOOL_KEY,
        "label": "Web Search",
        "description": "Search the web through the built-in Tavily integration configured from your environment.",
        "category": "Research",
        "provider": "tavily",
        "requires_auth": False,
        "capabilities": ["WEB_SEARCH"],
    },
    GMAIL_TOOL_KEY: {
        "key": GMAIL_TOOL_KEY,
        "label": "Gmail",
        "description": "Connect Google Gmail so your agents can read inbox results, send messages, and reply inside existing threads.",
        "category": "Email",
        "provider": "google",
        "requires_auth": True,
        "capabilities": GMAIL_CAPABILITIES,
    },
}

GOOGLE_GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def ensure_utc_datetime(value):
    if value is None:
        return None

    if not isinstance(value, datetime.datetime):
        return value

    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)

    return value.astimezone(datetime.timezone.utc)


def serialize_tool_config(doc: dict | None):
    if not doc:
        return None

    return {
        "tool_id": str(doc["_id"]),
        "tool_key": doc["tool_key"],
        "status": doc.get("status", "disconnected"),
        "connected": doc.get("status") == "connected",
        "provider": doc.get("provider"),
        "account_email": doc.get("account_email"),
        "configured_at": str(doc.get("configured_at")) if doc.get("configured_at") else None,
        "updated_at": str(doc.get("updated_at")) if doc.get("updated_at") else None,
    }


async def get_user_tool_configs(owner_id: str):
    docs = await tools_collection.find({"owner_id": ensure_object_id(owner_id)}).to_list(length=None)
    configs = {}

    for doc in docs:
        configs[doc["tool_key"]] = doc

    return configs


async def build_user_tool_catalog(owner_id: str):
    configured_tools = await get_user_tool_configs(owner_id)
    catalog = []

    for tool_key, definition in TOOL_DEFINITIONS.items():
        config = configured_tools.get(tool_key)
        connected = tool_key == WEB_SEARCH_TOOL_KEY or bool(config and config.get("status") == "connected")
        catalog.append({
            **definition,
            "status": "connected" if connected else "disconnected",
            "connected": connected,
            "config_required": definition["requires_auth"],
            "configurable": definition["requires_auth"],
            "configuration": serialize_tool_config(config),
        })

    return catalog


async def validate_agent_tools(tool_keys: list[str], owner_id: str):
    configured_tools = await get_user_tool_configs(owner_id)

    for tool_key in tool_keys:
        if tool_key not in TOOL_DEFINITIONS:
            return f"Unsupported tool selected: {tool_key}"

        if tool_key == WEB_SEARCH_TOOL_KEY:
            continue

        config = configured_tools.get(tool_key)
        if not config or config.get("status") != "connected":
            label = TOOL_DEFINITIONS[tool_key]["label"]
            return f"{label} must be configured in Tools before it can be added to an agent."

    return None


async def remove_tool_reference_from_agents(tool_key: str, owner_id: str):
    result = await agents_collection.update_many(
        {
            "owner_id": ObjectId(owner_id),
            "tools": tool_key,
        },
        {
            "$pull": {"tools": tool_key},
            "$set": {
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        },
    )

    return result.modified_count


def load_google_oauth_settings():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("Missing Google OAuth configuration in environment.")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
    }


def build_google_redirect_uri(base_url: str):
    return f"{base_url.rstrip('/')}/tools/google/callback"


def create_google_oauth_state(user_data: dict):
    payload = {
        "owner_id": str(user_data["_id"]),
        "email": user_data["email"],
        "purpose": "google_gmail_connect",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10),
    }
    return jwt.encode(payload, load_jwt_secret_key, algorithm="HS256")


def decode_google_oauth_state(state: str):
    return jwt.decode(state, load_jwt_secret_key, algorithms=["HS256"])


def build_google_auth_url(base_url: str, user_data: dict):
    oauth_settings = load_google_oauth_settings()
    state = create_google_oauth_state(user_data)

    query = urlencode({
        "client_id": oauth_settings["client_id"],
        "redirect_uri": build_google_redirect_uri(base_url),
        "response_type": "code",
        "scope": " ".join(GOOGLE_GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    })

    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def encode_redirect_message(message: str):
    return base64.urlsafe_b64encode(message.encode("utf-8")).decode("ascii")


def decode_redirect_message(message: str | None):
    if not message:
        return None

    try:
        return base64.urlsafe_b64decode(message.encode("ascii")).decode("utf-8")
    except Exception:
        return None


async def save_google_gmail_connection(owner_id: str, token_payload: dict, account_email: str):
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_in = int(token_payload.get("expires_in", 3600))
    document = {
        "tool_key": GMAIL_TOOL_KEY,
        "provider": "google",
        "status": "connected",
        "owner_id": ensure_object_id(owner_id),
        "account_email": account_email,
        "access_token": token_payload.get("access_token"),
        "refresh_token": token_payload.get("refresh_token"),
        "scope": token_payload.get("scope"),
        "token_type": token_payload.get("token_type", "Bearer"),
        "expires_at": now + datetime.timedelta(seconds=expires_in),
        "configured_at": now,
        "updated_at": now,
    }

    existing = await tools_collection.find_one({
        "owner_id": ensure_object_id(owner_id),
        "tool_key": GMAIL_TOOL_KEY,
    })

    if existing and not document["refresh_token"]:
        document["refresh_token"] = existing.get("refresh_token")
        document["configured_at"] = existing.get("configured_at", now)

    await tools_collection.update_one(
        {
            "owner_id": ensure_object_id(owner_id),
            "tool_key": GMAIL_TOOL_KEY,
        },
        {"$set": document},
        upsert=True,
    )


def exchange_google_code_for_tokens(code: str, base_url: str):
    oauth_settings = load_google_oauth_settings()

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": oauth_settings["client_id"],
            "client_secret": oauth_settings["client_secret"],
            "redirect_uri": build_google_redirect_uri(base_url),
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def fetch_google_gmail_profile(access_token: str):
    response = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def refresh_google_access_token(refresh_token: str):
    oauth_settings = load_google_oauth_settings()

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": oauth_settings["client_id"],
            "client_secret": oauth_settings["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


async def get_valid_gmail_access_token(tool_config: dict):
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = ensure_utc_datetime(tool_config.get("expires_at"))
    access_token = tool_config.get("access_token")

    if access_token and expires_at and expires_at > now + datetime.timedelta(minutes=1):
        return access_token

    refresh_token = tool_config.get("refresh_token")
    if not refresh_token:
        raise ValueError("Gmail access has expired and no refresh token is available. Please reconnect Gmail.")

    refreshed = refresh_google_access_token(refresh_token)
    new_access_token = refreshed.get("access_token")
    if not new_access_token:
        raise ValueError("Failed to refresh Gmail access token.")

    new_expiry = now + datetime.timedelta(seconds=int(refreshed.get("expires_in", 3600)))
    await tools_collection.update_one(
        {"_id": tool_config["_id"]},
        {
            "$set": {
                "access_token": new_access_token,
                "scope": refreshed.get("scope", tool_config.get("scope")),
                "token_type": refreshed.get("token_type", tool_config.get("token_type", "Bearer")),
                "expires_at": new_expiry,
                "updated_at": now,
            }
        },
    )

    logger.info("Refreshed Gmail access token successfully")
    return new_access_token


async def disconnect_gmail_tool(owner_id: str):
    tool_config = await tools_collection.find_one({
        "owner_id": ensure_object_id(owner_id),
        "tool_key": GMAIL_TOOL_KEY,
    })

    if not tool_config:
        return False

    token_to_revoke = tool_config.get("refresh_token") or tool_config.get("access_token")
    if token_to_revoke:
        try:
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": token_to_revoke},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
        except Exception as exc:
            logger.warning(f"Google token revoke failed during disconnect: {exc}")

    removed_from_agents = await remove_tool_reference_from_agents(GMAIL_TOOL_KEY, owner_id)
    await tools_collection.delete_one({"_id": tool_config["_id"]})
    return {
        "disconnected": True,
        "removed_from_agents": removed_from_agents,
    }
