import secrets
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.redis import get_redis_dep
from app.core.security import encrypt_token, decode_access_token
from app.core.logging import get_logger
from app.models.social_account import SocialAccount
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.meta_service import exchange_code_for_long_lived_token, get_auth_url, get_user_pages, get_pages_by_known_ids

logger = get_logger(__name__)
router = APIRouter(prefix="/social-accounts", tags=["social-accounts"])

OAUTH_STATE_TTL = 600  # 10 minutes


@router.get("")
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SocialAccount).where(SocialAccount.user_id == current_user.id, SocialAccount.is_active == True)
    )
    accounts = result.scalars().all()
    return [
        {
            "id": a.id,
            "platform": a.platform,
            "page_id": a.page_id,
            "page_name": a.page_name,
            "page_picture_url": a.page_picture_url,
            "instagram_account_id": a.instagram_account_id,
            "token_expires_at": a.token_expires_at.isoformat() if a.token_expires_at else None,
            "connected_at": a.connected_at.isoformat() if a.connected_at else None,
        }
        for a in accounts
    ]


@router.get("/meta/auth-url")
async def meta_auth_url(
    redis: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    state = secrets.token_urlsafe(24)
    # Store user_id keyed by state token so callback can look up who initiated
    await redis.setex(f"oauth_state:{state}", OAUTH_STATE_TTL, current_user.id)
    return {"auth_url": get_auth_url(state)}


@router.get("/meta/callback")
async def meta_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    frontend_settings = "http://localhost:3000/settings"

    if error or not code or not state:
        return RedirectResponse(f"{frontend_settings}?error=oauth_denied")

    # Validate state and retrieve user_id
    user_id = await redis.get(f"oauth_state:{state}")
    if not user_id:
        return RedirectResponse(f"{frontend_settings}?error=invalid_state")
    await redis.delete(f"oauth_state:{state}")

    user_id = user_id.decode() if isinstance(user_id, bytes) else user_id

    try:
        token_data = await exchange_code_for_long_lived_token(code)
        long_token = token_data["access_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

        pages = await get_user_pages(long_token)
        logger.info("meta_pages_count", count=len(pages))

        # Fallback: if no pages returned, try to refresh existing DB accounts for this user
        if not pages:
            existing_result = await db.execute(
                select(SocialAccount).where(SocialAccount.user_id == user_id)
            )
            existing_accounts = existing_result.scalars().all()
            if existing_accounts:
                # Try to get page token directly using the known page ID + user token
                pages = await get_pages_by_known_ids(
                    long_token, [a.page_id for a in existing_accounts]
                )
                logger.info("meta_pages_fallback", count=len(pages))

        if not pages:
            return RedirectResponse(f"{frontend_settings}?error=no_pages_found_select_page_in_dialog")

        from ulid import ULID
        saved = 0
        for page in pages:
            # Upsert: update if page already connected
            existing = await db.execute(
                select(SocialAccount).where(
                    SocialAccount.platform == "facebook",
                    SocialAccount.page_id == page["page_id"],
                )
            )
            account = existing.scalar_one_or_none()

            if account:
                account.access_token = encrypt_token(page["page_token"])
                account.token_expires_at = expires_at
                account.instagram_account_id = page["instagram_account_id"]
                account.is_active = True
                account.last_verified_at = datetime.now(timezone.utc)
            else:
                account = SocialAccount(
                    id=str(ULID()),
                    user_id=user_id,
                    platform="facebook",
                    page_id=page["page_id"],
                    page_name=page["page_name"],
                    page_picture_url=page.get("page_picture_url"),
                    instagram_account_id=page["instagram_account_id"],
                    access_token=encrypt_token(page["page_token"]),
                    token_expires_at=expires_at,
                    is_active=True,
                )
                db.add(account)
            saved += 1

        await db.commit()
        logger.info("meta_oauth_complete", user_id=user_id, pages_saved=saved)
        return RedirectResponse(f"{frontend_settings}?connected={saved}")

    except Exception as exc:
        logger.exception("meta_oauth_error", error=str(exc))
        return RedirectResponse(f"{frontend_settings}?error=oauth_failed")


@router.delete("/{account_id}")
async def disconnect_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")
    account.is_active = False
    await db.commit()
    return {"status": "disconnected"}
