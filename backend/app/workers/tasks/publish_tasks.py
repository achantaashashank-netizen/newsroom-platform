import asyncio
from datetime import datetime, timedelta, timezone

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_sync_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, name="app.workers.tasks.publish_tasks.publish_story_task")
def publish_story_task(self, publication_id: str):
    """Publishes a story to the configured Meta platform. Runs in Celery worker."""
    from sqlalchemy.orm import Session
    from app.models.publication import Publication
    from app.models.story import Story
    from app.models.social_account import SocialAccount
    from app.core.security import decrypt_token

    db: Session = _get_sync_db()
    try:
        pub = db.get(Publication, publication_id)
        if not pub:
            logger.error("publication_not_found", publication_id=publication_id)
            return

        story = db.get(Story, pub.story_id)
        if not story:
            logger.error("story_not_found", story_id=pub.story_id)
            return

        # Instagram is stored under the linked Facebook page account
        if pub.platform == "instagram":
            account = db.query(SocialAccount).filter(
                SocialAccount.instagram_account_id == pub.page_id,
                SocialAccount.is_active == True,
            ).first()
        else:
            account = db.query(SocialAccount).filter_by(
                platform=pub.platform,
                page_id=pub.page_id,
                is_active=True,
            ).first()

        if not account:
            pub.status = "failed"
            pub.error_message = f"No active {pub.platform} account for page {pub.page_id}"
            db.commit()
            return

        token = decrypt_token(account.access_token)

        if pub.platform == "facebook":
            post_id = _publish_facebook(story, token, account.page_id)
        elif pub.platform == "instagram":
            post_id = _publish_instagram(story, token, pub.page_id)
        else:
            pub.status = "failed"
            pub.error_message = f"Unknown platform: {pub.platform}"
            db.commit()
            return

        pub.platform_post_id = post_id
        pub.status = "published"
        pub.published_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("published", publication_id=publication_id, platform=pub.platform, post_id=post_id)

    except Exception as exc:
        logger.exception("publish_task_error", publication_id=publication_id, error=str(exc))
        if pub:
            pub.status = "failed"
            pub.error_message = str(exc)
            pub.retry_count = (pub.retry_count or 0) + 1
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


def _read_local_image(url_or_path: str) -> bytes | None:
    """Read image bytes — handles /media/... local paths and http URLs."""
    import httpx
    from pathlib import Path
    from app.core.config import settings

    if url_or_path and url_or_path.startswith("/media/"):
        filename = url_or_path.split("/media/")[-1]
        local = Path(settings.MEDIA_DIR) / filename
        if local.exists():
            return local.read_bytes()
    if url_or_path and url_or_path.startswith("http"):
        try:
            r = httpx.get(url_or_path, timeout=20.0, follow_redirects=True)
            r.raise_for_status()
            return r.content
        except Exception:
            pass
    return None


def _publish_facebook(story, token: str, page_id: str) -> str:
    import httpx
    base = "https://graph.facebook.com/v21.0"

    # Use platform-specific social card if available, else selected image
    social_cards = story.social_card_paths or {}
    image_source = social_cards.get("facebook") or story.selected_image_url

    photo_id = None
    if image_source:
        image_bytes = _read_local_image(image_source)
        if image_bytes:
            resp = httpx.post(
                f"{base}/{page_id}/photos",
                params={"published": "false", "access_token": token},
                files={"source": ("image.jpg", image_bytes, "image/jpeg")},
                timeout=60.0,
            )
        else:
            resp = httpx.post(f"{base}/{page_id}/photos", params={
                "url": image_source,
                "published": False,
                "access_token": token,
            }, timeout=30.0)
        resp.raise_for_status()
        photo_id = resp.json().get("id")

    post_data = {
        "message": story.caption_facebook or story.headline or "",
        "access_token": token,
    }
    if photo_id:
        post_data["attached_media"] = f'[{{"media_fbid":"{photo_id}"}}]'

    resp = httpx.post(f"{base}/{page_id}/feed", params=post_data, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["id"]


def _publish_instagram(story, token: str, ig_account_id: str) -> str:
    import httpx
    import time
    base = "https://graph.facebook.com/v21.0"

    social_cards = story.social_card_paths or {}
    image_source = social_cards.get("instagram") or story.selected_image_url

    if not image_source:
        raise ValueError("Instagram requires an image")

    # Instagram container API requires a public URL — upload to FB first as a workaround
    # Try direct URL; if local, upload via FB CDN trick using page token
    image_bytes = _read_local_image(image_source)

    if image_bytes:
        # Upload to Facebook as unpublished photo to get a public CDN URL
        # Use the linked page token (same account)
        fb_resp = httpx.post(
            f"{base}/me/photos",
            params={"published": "false", "access_token": token},
            files={"source": ("image.jpg", image_bytes, "image/jpeg")},
            timeout=60.0,
        )
        fb_resp.raise_for_status()
        # Get the photo's CDN URL
        photo_id = fb_resp.json().get("id")
        cdn_resp = httpx.get(f"{base}/{photo_id}", params={
            "fields": "images",
            "access_token": token,
        }, timeout=15.0)
        cdn_resp.raise_for_status()
        images = cdn_resp.json().get("images", [])
        public_url = images[0]["source"] if images else None
    else:
        public_url = image_source if image_source.startswith("http") else None

    if not public_url:
        raise ValueError("Could not obtain public image URL for Instagram")

    # Step 1: Create media container
    resp = httpx.post(f"{base}/{ig_account_id}/media", params={
        "image_url": public_url,
        "caption": story.caption_instagram or story.headline or "",
        "access_token": token,
    }, timeout=30.0)
    resp.raise_for_status()
    container_id = resp.json()["id"]

    # Step 2: Poll until FINISHED
    for _ in range(10):
        status_resp = httpx.get(f"{base}/{container_id}", params={
            "fields": "status_code",
            "access_token": token,
        }, timeout=15.0)
        if status_resp.json().get("status_code") == "FINISHED":
            break
        time.sleep(2)

    # Step 3: Publish
    resp = httpx.post(f"{base}/{ig_account_id}/media_publish", params={
        "creation_id": container_id,
        "access_token": token,
    }, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["id"]


@celery_app.task(name="app.workers.tasks.publish_tasks.refresh_expiring_tokens")
def refresh_expiring_tokens():
    """Refreshes Meta tokens expiring within 7 days. Runs daily at 3am UTC."""
    from app.models.social_account import SocialAccount
    from app.core.security import decrypt_token, encrypt_token
    import httpx

    db = _get_sync_db()
    try:
        cutoff = datetime.now(timezone.utc) + timedelta(days=7)
        accounts = db.query(SocialAccount).filter(
            SocialAccount.token_expires_at < cutoff,
            SocialAccount.is_active == True,
        ).all()

        from app.core.config import settings
        for account in accounts:
            try:
                old_token = decrypt_token(account.access_token)
                resp = httpx.get("https://graph.facebook.com/v21.0/oauth/access_token", params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "fb_exchange_token": old_token,
                }, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()
                account.access_token = encrypt_token(data["access_token"])
                account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 5184000))
                logger.info("token_refreshed", platform=account.platform, page_id=account.page_id)
            except Exception as exc:
                logger.warning("token_refresh_failed", page_id=account.page_id, error=str(exc))

        db.commit()
    finally:
        db.close()
