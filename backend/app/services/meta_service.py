import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"
SCOPES = "pages_manage_posts,pages_read_engagement,instagram_basic,instagram_content_publish,pages_show_list"


def get_auth_url(state: str) -> str:
    params = (
        f"client_id={settings.META_APP_ID}"
        f"&redirect_uri={settings.META_REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&state={state}"
        f"&response_type=code"
    )
    return f"https://www.facebook.com/v21.0/dialog/oauth?{params}"


async def exchange_code_for_long_lived_token(code: str) -> dict:
    """Exchange auth code → short-lived token → long-lived (60-day) token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: code → short-lived token
        resp = await client.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": settings.META_REDIRECT_URI,
            "code": code,
        })
        resp.raise_for_status()
        short_token = resp.json()["access_token"]

        # Step 2: short-lived → long-lived
        resp2 = await client.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": short_token,
        })
        resp2.raise_for_status()
        data = resp2.json()
        return {
            "access_token": data["access_token"],
            "expires_in": data.get("expires_in", 5184000),  # ~60 days default
        }


async def debug_token_permissions(user_token: str) -> dict:
    """Check what permissions the user token actually has."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{GRAPH_BASE}/debug_token", params={
            "input_token": user_token,
            "access_token": f"{settings.META_APP_ID}|{settings.META_APP_SECRET}",
        })
        data = resp.json().get("data", {})
        scopes = data.get("scopes", [])
        logger.info("token_debug", scopes=scopes, user_id=data.get("user_id"), is_valid=data.get("is_valid"))
        return data


async def get_pages_by_known_ids(user_token: str, page_ids: list[str]) -> list[dict]:
    """Fallback: directly fetch page tokens for known page IDs using the user token."""
    result = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for page_id in page_ids:
            try:
                resp = await client.get(f"{GRAPH_BASE}/{page_id}", params={
                    "fields": "id,name,access_token,instagram_business_account",
                    "access_token": user_token,
                })
                logger.info("direct_page_fetch", page_id=page_id, status=resp.status_code, body=resp.text[:300])
                data = resp.json()
                if "access_token" in data:
                    ig_data = data.get("instagram_business_account", {})
                    result.append({
                        "page_id": data["id"],
                        "page_name": data["name"],
                        "page_picture_url": None,
                        "page_token": data["access_token"],
                        "instagram_account_id": ig_data.get("id") if ig_data else None,
                    })
            except Exception as e:
                logger.warning("direct_page_fetch_error", page_id=page_id, error=str(e))
    return result


async def get_user_pages(user_token: str) -> list[dict]:
    """Fetch all Facebook Pages managed by this user + their linked IG accounts."""
    # Debug what permissions the token actually has
    await debug_token_permissions(user_token)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{GRAPH_BASE}/me/accounts", params={
            "fields": "id,name,access_token",
            "access_token": user_token,
            "limit": 100,
        })
        logger.info("meta_pages_response", status=resp.status_code, body=resp.text[:1000])
        resp.raise_for_status()
        body = resp.json()
        pages = body.get("data", [])
        if not pages:
            logger.warning("meta_pages_empty", full_response=body)

        result = []
        for page in pages:
            page_data = {
                "page_id": page["id"],
                "page_name": page["name"],
                "page_picture_url": None,
                "page_token": page["access_token"],
                "instagram_account_id": None,
            }
            # Fetch linked Instagram Business Account
            try:
                ig_resp = await client.get(f"{GRAPH_BASE}/{page['id']}", params={
                    "fields": "instagram_business_account",
                    "access_token": page["access_token"],
                })
                ig_data = ig_resp.json().get("instagram_business_account", {})
                if ig_data:
                    page_data["instagram_account_id"] = ig_data.get("id")
            except Exception:
                pass
            result.append(page_data)

        return result
