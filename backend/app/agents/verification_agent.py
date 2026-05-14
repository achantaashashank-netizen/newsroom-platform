import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.agents.state import NewsroomState, VerificationResult
from app.core.config import settings
from app.core.logging import get_logger
from app.tools.source_db import get_source_reliability

logger = get_logger(__name__)


def _extract_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain
    except Exception:
        return ""


def _compute_confidence(
    verification_results: list[VerificationResult],
    source_reliability_scores: dict,
) -> tuple[float, str]:
    if not verification_results:
        return 0.0, "low"

    corroborated = [r for r in verification_results if r["corroborated"]]
    corroboration_rate = len(corroborated) / len(verification_results)

    reliability_scores = list(source_reliability_scores.values())
    avg_reliability = sum(reliability_scores) / len(reliability_scores) if reliability_scores else 0.5

    confidence = (corroboration_rate * 0.6) + (avg_reliability * 0.4)
    confidence = round(min(max(confidence, 0.0), 1.0), 4)

    if confidence < settings.CONFIDENCE_LOW_THRESHOLD:
        tier = "low"
    elif confidence < settings.CONFIDENCE_HIGH_THRESHOLD:
        tier = "medium"
    else:
        tier = "high"

    return confidence, tier


def _detect_fake_news_flags(sources: list) -> list[str]:
    flags: list[str] = []
    domains = [_extract_domain(s["url"]) for s in sources]

    known_unreliable = {"naturalews.com", "infowars.com", "breitbart.com", "beforeitsnews.com"}
    flagged_domains = known_unreliable.intersection(set(domains))
    if flagged_domains:
        flags.append(f"Low-credibility sources detected: {', '.join(flagged_domains)}")

    if len(sources) < 2:
        flags.append("Insufficient sources — fewer than 2 articles found")

    unique_domains = set(domains)
    if len(unique_domains) < 2:
        flags.append("Single-source story — could not verify across multiple outlets")

    return flags


async def _verify_source(
    client: httpx.AsyncClient,
    source: dict,
    query_keywords: list[str],
    all_sources: list[dict],
) -> VerificationResult:
    url = source["url"]
    domain = _extract_domain(url)
    reliability = get_source_reliability(url)

    # Cross-corroboration: check if other sources mention the same key entities
    title_words = set(source["title"].lower().split())
    significant_words = {w for w in title_words if len(w) > 4}

    claim_matches: list[str] = []
    contradictions: list[str] = []

    for other in all_sources:
        if other["url"] == url:
            continue
        other_text = f"{other['title']} {other['raw_text']}".lower()
        matches = significant_words.intersection(set(other_text.split()))
        if len(matches) >= 3:
            claim_matches.append(other["source_name"])

    corroborated = len(claim_matches) >= 1  # At least one other source confirms

    return {
        "source_url": url,
        "source_name": source["source_name"],
        "corroborated": corroborated,
        "confidence_contribution": reliability * (1.2 if corroborated else 0.6),
        "reliability_score": reliability,
        "claim_matches": claim_matches[:5],
        "contradictions": contradictions,
    }


async def verification_node(state: NewsroomState) -> dict:
    run_id = state["run_id"]
    raw_sources = state.get("raw_sources", [])
    query = state["query"]

    logs = [{
        "node": "verification_node",
        "type": "start",
        "message": f"Verifying {len(raw_sources)} sources for authenticity and cross-corroboration",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]

    if not raw_sources:
        logs.append({
            "node": "verification_node",
            "type": "done",
            "message": "No sources to verify — story will be rejected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "verification_results": [],
            "overall_confidence": 0.0,
            "confidence_tier": "low",
            "fake_news_flags": ["No sources discovered"],
            "source_reliability_scores": {},
            "current_node": "verification_node",
            "agent_logs": logs,
        }

    query_keywords = query.lower().split()[:5]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
                _verify_source(client, source, query_keywords, raw_sources)
                for source in raw_sources[:20]  # cap at 20 sources for speed
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        verification_results: list[VerificationResult] = []
        source_reliability_scores: dict[str, float] = {}

        for i, result in enumerate(results):
            if isinstance(result, VerificationResult.__class__) or isinstance(result, dict):
                verification_results.append(result)
                source_reliability_scores[result["source_url"]] = result["reliability_score"]
            else:
                logger.warning("verification_item_error", error=str(result), index=i)

        logs.append({
            "node": "verification_node",
            "type": "progress",
            "message": f"Cross-referenced {len(verification_results)} sources — computing confidence score",
            "progress": 70,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        overall_confidence, confidence_tier = _compute_confidence(
            verification_results, source_reliability_scores
        )

        corroborated_count = sum(1 for r in verification_results if r["corroborated"])
        fake_news_flags = _detect_fake_news_flags(raw_sources)

        logs.append({
            "node": "verification_node",
            "type": "done",
            "message": (
                f"Verification complete — {corroborated_count}/{len(verification_results)} sources corroborated. "
                f"Confidence: {overall_confidence:.0%} ({confidence_tier.upper()})"
            ),
            "progress": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(
            "verification_complete",
            run_id=run_id,
            confidence=overall_confidence,
            tier=confidence_tier,
            corroborated=corroborated_count,
        )

        return {
            "verification_results": verification_results,
            "overall_confidence": overall_confidence,
            "confidence_tier": confidence_tier,
            "fake_news_flags": fake_news_flags,
            "source_reliability_scores": source_reliability_scores,
            "current_node": "verification_node",
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.exception("verification_error", run_id=run_id, error=str(exc))
        logs.append({
            "node": "verification_node",
            "type": "error",
            "message": f"Verification error: {exc}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "verification_results": [],
            "overall_confidence": 0.0,
            "confidence_tier": "low",
            "fake_news_flags": [f"Verification error: {exc}"],
            "source_reliability_scores": {},
            "error": str(exc),
            "current_node": "verification_node",
            "agent_logs": logs,
        }
