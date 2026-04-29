from urllib.parse import quote

import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from utils.loggers import logger
from utils.response import error_response, success_response
from utils.tool_helpers import (
    GMAIL_TOOL_KEY,
    build_google_auth_url,
    build_user_tool_catalog,
    decode_google_oauth_state,
    disconnect_gmail_tool,
    encode_redirect_message,
    exchange_google_code_for_tokens,
    fetch_google_gmail_profile,
    save_google_gmail_connection,
)
from utils.users import get_current_user


tool_config_router = APIRouter(prefix="/tools", tags=["Tools"])

#- gmail
def _redirect_to_tools(status: str, message: str):
    encoded_message = quote(encode_redirect_message(message))
    return RedirectResponse(url=f"/#tools?google_status={status}&message={encoded_message}", status_code=302)


@tool_config_router.get("/catalog")
async def get_tool_catalog(current_user: dict = Depends(get_current_user)):
    logger.info(f"Tool catalog requested by {current_user['email']}")
    catalog = await build_user_tool_catalog(current_user["_id"])
    return success_response(200, data=catalog, message="Tool catalog fetched successfully.")


@tool_config_router.get("/google/connect-url")
async def get_google_connect_url(request: Request, current_user: dict = Depends(get_current_user)):
    logger.info(f"Google connect URL requested by {current_user['email']}")
    auth_url = build_google_auth_url(str(request.base_url).rstrip("/"), current_user)
    return success_response(200, data={"auth_url": auth_url}, message="Google auth URL generated successfully.")


@tool_config_router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        logger.warning(f"Google OAuth returned an error: {error}")
        return _redirect_to_tools("error", "Google sign-in was cancelled or denied.")

    if not code or not state:
        return _redirect_to_tools("error", "Google OAuth callback is missing required parameters.")

    try:
        oauth_state = decode_google_oauth_state(state)
        if oauth_state.get("purpose") != "google_gmail_connect":
            return _redirect_to_tools("error", "Invalid Google OAuth state.")

        tokens = exchange_google_code_for_tokens(code, str(request.base_url).rstrip("/"))
        profile = fetch_google_gmail_profile(tokens["access_token"])
        account_email = profile.get("emailAddress")
        if not account_email:
            return _redirect_to_tools("error", "Could not determine the connected Gmail account.")

        await save_google_gmail_connection(oauth_state["owner_id"], tokens, account_email)
        logger.info(f"Gmail connected successfully for {oauth_state['email']}")
        return _redirect_to_tools("connected", f"Gmail connected for {account_email}.")

    except jwt.ExpiredSignatureError:
        logger.warning("Google OAuth state expired")
        return _redirect_to_tools("error", "Google connect session expired. Please try again.")
    except jwt.InvalidTokenError:
        logger.warning("Google OAuth state invalid")
        return _redirect_to_tools("error", "Google connect session was invalid.")
    except requests.HTTPError as exc:
        logger.error(f"Google OAuth HTTP failure: {exc}")
        return _redirect_to_tools("error", "Google OAuth failed while exchanging or verifying tokens.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Gmail connection failed: {exc}")
        return _redirect_to_tools("error", "Failed to connect Gmail.")


@tool_config_router.delete("/disconnect/{tool_key}")
async def disconnect_tool(tool_key: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Tool disconnect requested for {tool_key} by {current_user['email']}")

    if tool_key != GMAIL_TOOL_KEY:
        return error_response(400, message="Only Gmail requires disconnect flow.")

    disconnect_result = await disconnect_gmail_tool(current_user["_id"])
    if not disconnect_result:
        return error_response(404, message="Gmail is not connected.")

    return success_response(
        200,
        data={"removed_from_agents": disconnect_result["removed_from_agents"]},
        message="Gmail disconnected successfully.",
    )
