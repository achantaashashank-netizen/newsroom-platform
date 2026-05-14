import urllib.parse
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MEDIA_DIR = Path(settings.MEDIA_DIR)

_PROMPT_TEMPLATE = (
    "Editorial cartoon illustration for a news article. "
    "Headline: {headline}. "
    "Context: {context}. "
    "Style: vibrant flat-design digital illustration, bold saturated colors, "
    "editorial magazine quality similar to The Economist or TIME magazine covers, "
    "clean professional look, highly relevant visual metaphors, "
    "NO text, NO words, NO letters, NO numbers anywhere in the image."
)


def _ensure_media_dir() -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def _save_image_bytes(image_bytes: bytes, run_id: str) -> str:
    local_filename = f"{run_id}_cartoon.jpg"
    local_path = MEDIA_DIR / local_filename
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img.save(local_path, "JPEG", quality=95)
    return f"/media/{local_filename}"


def _build_prompt(headline: str, summary: str, bullet_points: list[str]) -> str:
    context = ". ".join(bullet_points[:3]) if bullet_points else (summary[:300] if summary else "")
    return _PROMPT_TEMPLATE.format(headline=headline[:200], context=context[:300])


# ── Generator 1: OpenAI gpt-image-1 ──────────────────────────────────────────

async def _try_openai(prompt: str, run_id: str) -> str | None:
    if not settings.OPENAI_API_KEY:
        return None
    try:
        import base64
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("image_gen_trying", provider="openai", run_id=run_id)
        resp = await client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1536x1024",
            n=1,
        )
        item = resp.data[0]
        if getattr(item, "b64_json", None):
            image_bytes = base64.b64decode(item.b64_json)
        elif getattr(item, "url", None):
            async with httpx.AsyncClient(timeout=30.0) as dl:
                r = await dl.get(item.url, follow_redirects=True)
                r.raise_for_status()
                image_bytes = r.content
        else:
            return None
        _ensure_media_dir()
        path = _save_image_bytes(image_bytes, run_id)
        logger.info("image_gen_success", provider="openai", run_id=run_id)
        return path
    except Exception as exc:
        logger.warning("image_gen_failed", provider="openai", error=str(exc), run_id=run_id)
        return None


# ── Generator 2: Hugging Face FLUX.1-schnell (free tier) ─────────────────────

async def _try_huggingface(prompt: str, run_id: str) -> str | None:
    if not settings.HF_TOKEN:
        return None
    try:
        logger.info("image_gen_trying", provider="huggingface", run_id=run_id)
        headers = {"Authorization": f"Bearer {settings.HF_TOKEN}"}
        payload = {
            "inputs": prompt,
            "parameters": {"width": 1344, "height": 768, "num_inference_steps": 4},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning("image_gen_failed", provider="huggingface", error=f"unexpected content-type: {content_type}", run_id=run_id)
                return None
            image_bytes = resp.content
        _ensure_media_dir()
        path = _save_image_bytes(image_bytes, run_id)
        logger.info("image_gen_success", provider="huggingface", run_id=run_id)
        return path
    except Exception as exc:
        logger.warning("image_gen_failed", provider="huggingface", error=str(exc), run_id=run_id)
        return None


# ── Generator 3: Pollinations.ai (no key required) ───────────────────────────

async def _try_pollinations(prompt: str, run_id: str) -> str | None:
    try:
        logger.info("image_gen_trying", provider="pollinations", run_id=run_id)
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1344&height=768&model=flux&nologo=true&seed={abs(hash(run_id)) % 9999}"
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                return None
            image_bytes = resp.content
        _ensure_media_dir()
        path = _save_image_bytes(image_bytes, run_id)
        logger.info("image_gen_success", provider="pollinations", run_id=run_id)
        return path
    except Exception as exc:
        logger.warning("image_gen_failed", provider="pollinations", error=str(exc), run_id=run_id)
        return None


# ── Generator 4: newspaper3k article image fallback ──────────────────────────

async def fetch_article_image(source_urls: list[str], run_id: str) -> str | None:
    import asyncio
    from newspaper import Article

    _ensure_media_dir()

    def _extract(url: str) -> str | None:
        try:
            a = Article(url, request_timeout=8)
            a.download()
            a.parse()
            if a.top_image and a.top_image.startswith("http"):
                return a.top_image
        except Exception:
            pass
        return None

    loop = asyncio.get_event_loop()
    for url in source_urls[:5]:
        image_url = await loop.run_in_executor(None, _extract, url)
        if not image_url:
            continue
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                r = await client.get(image_url)
                r.raise_for_status()
                if not r.headers.get("content-type", "").startswith("image/"):
                    continue
                image_bytes = r.content
            _ensure_media_dir()
            path = _save_image_bytes(image_bytes, run_id)
            logger.info("article_image_saved", run_id=run_id, source=url)
            return path
        except Exception:
            continue
    return None


# ── Public entry point ────────────────────────────────────────────────────────

async def generate_dalle_cartoon(
    run_id: str,
    headline: str,
    summary: str,
    bullet_points: list[str],
) -> str | None:
    """Try OpenAI → Hugging Face → Pollinations in order. Returns /media/<file> or None."""
    prompt = _build_prompt(headline, summary, bullet_points)

    result = await _try_openai(prompt, run_id)
    if result:
        return result

    result = await _try_huggingface(prompt, run_id)
    if result:
        return result

    result = await _try_pollinations(prompt, run_id)
    return result


# ── Social card generator (unchanged) ─────────────────────────────────────────

def _load_font(size: int):
    from PIL import ImageFont
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    from PIL import ImageDraw, Image as PilImage
    draw = ImageDraw.Draw(PilImage.new("RGB", (1, 1)))
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_social_card(
    headline: str,
    source_name: str,
    image_source: str,
    platform: str,
    run_id: str,
) -> str | None:
    from PIL import ImageDraw, ImageEnhance
    _ensure_media_dir()
    w, h = (1200, 630) if platform == "facebook" else (1080, 1080)

    try:
        img = Image.new("RGB", (w, h), color=(15, 15, 25))

        local_cartoon = MEDIA_DIR / f"{run_id}_cartoon.jpg"
        bg_loaded = False

        if local_cartoon.exists():
            try:
                bg = Image.open(local_cartoon).convert("RGB")
                bg_loaded = True
            except Exception:
                pass

        if not bg_loaded and image_source and image_source.startswith("http"):
            try:
                response = httpx.get(image_source, timeout=12.0, follow_redirects=True)
                response.raise_for_status()
                bg = Image.open(BytesIO(response.content)).convert("RGB")
                bg_loaded = True
            except Exception:
                pass

        if bg_loaded:
            bg_ratio = bg.width / bg.height
            card_ratio = w / h
            if bg_ratio > card_ratio:
                new_w = int(bg.height * card_ratio)
                offset = (bg.width - new_w) // 2
                bg = bg.crop((offset, 0, offset + new_w, bg.height))
            else:
                new_h = int(bg.width / card_ratio)
                offset = (bg.height - new_h) // 2
                bg = bg.crop((0, offset, bg.width, offset + new_h))
            bg = bg.resize((w, h), Image.LANCZOS)
            bg = ImageEnhance.Brightness(bg).enhance(0.5)
            img.paste(bg, (0, 0))

        draw = ImageDraw.Draw(img)

        overlay_h = int(h * 0.50)
        overlay = Image.new("RGBA", (w, overlay_h), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        for i in range(overlay_h):
            alpha = int(230 * (i / overlay_h))
            ov_draw.rectangle([(0, i), (w, i + 1)], fill=(8, 8, 18, alpha))
        img.paste(
            Image.alpha_composite(Image.new("RGBA", (w, overlay_h), (0, 0, 0, 0)), overlay).convert("RGB"),
            (0, h - overlay_h),
            mask=overlay.split()[3],
        )

        padding = int(w * 0.05)
        text_w = w - padding * 2
        headline_font = _load_font(int(w * 0.038))
        brand_font = _load_font(int(w * 0.022))

        brand_text = f"NEWSROOM"
        brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        pill_w = brand_bbox[2] - brand_bbox[0] + 24
        pill_h = brand_bbox[3] - brand_bbox[1] + 12
        draw.rounded_rectangle(
            [padding, int(h * 0.06), padding + pill_w, int(h * 0.06) + pill_h],
            radius=6, fill=(99, 102, 241),
        )
        draw.text((padding + 12, int(h * 0.06) + 6), brand_text, font=brand_font, fill=(255, 255, 255))

        lines = _wrap_text(headline, headline_font, text_w)[:4]
        line_h = int(w * 0.048)
        total_text_h = len(lines) * line_h
        y = h - padding - total_text_h - int(h * 0.03)
        for line in lines:
            draw.text((padding, y), line, font=headline_font, fill=(245, 245, 255))
            y += line_h

        filename = f"{run_id}_{platform}.jpg"
        path = MEDIA_DIR / filename
        img.save(path, "JPEG", quality=92)
        return f"/media/{filename}"

    except Exception as exc:
        logger.warning("social_card_error", platform=platform, error=str(exc))
        return None
