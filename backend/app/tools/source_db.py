"""
Static source reliability database.
Scores are 0.0 (unreliable) to 1.0 (highly reliable).
Based on media bias / factual reporting ratings.
"""

SOURCE_RELIABILITY: dict[str, float] = {
    # Wire services (highest reliability)
    "reuters.com": 0.95,
    "apnews.com": 0.95,
    "afp.com": 0.92,
    "bloomberg.com": 0.90,
    "wsj.com": 0.88,

    # Major newspapers
    "nytimes.com": 0.87,
    "washingtonpost.com": 0.85,
    "theguardian.com": 0.85,
    "bbc.com": 0.88,
    "bbc.co.uk": 0.88,
    "ft.com": 0.88,
    "economist.com": 0.87,
    "latimes.com": 0.82,
    "usatoday.com": 0.78,
    "npr.org": 0.85,
    "pbs.org": 0.84,

    # International
    "dw.com": 0.85,
    "aljazeera.com": 0.78,
    "france24.com": 0.80,
    "abc.net.au": 0.83,
    "cbc.ca": 0.84,
    "thehindu.com": 0.80,

    # Business / Finance
    "techcrunch.com": 0.75,
    "wired.com": 0.78,
    "arstechnica.com": 0.80,
    "theverge.com": 0.75,
    "cnbc.com": 0.80,
    "fortune.com": 0.78,
    "businessinsider.com": 0.70,
    "forbes.com": 0.72,
    "marketwatch.com": 0.78,
    "barrons.com": 0.82,

    # Tech (additional)
    "technologyreview.com": 0.85,  # MIT Tech Review
    "9to5mac.com": 0.70,
    "venturebeat.com": 0.72,
    "zdnet.com": 0.73,

    # Science / Health
    "sciencedaily.com": 0.82,
    "nature.com": 0.95,
    "sciencemag.org": 0.95,
    "newscientist.com": 0.82,
    "livescience.com": 0.75,
    "statnews.com": 0.83,
    "medscape.com": 0.80,

    # Environment
    "insideclimatenews.org": 0.80,
    "climatechangenews.com": 0.75,

    # Politics
    "politico.com": 0.80,
    "thehill.com": 0.75,
    "rollcall.com": 0.78,
    "axios.com": 0.80,

    # More US
    "nbcnews.com": 0.78,
    "cbsnews.com": 0.78,
    "abcnews.go.com": 0.78,
    "latimes.com": 0.82,
    "chicagotribune.com": 0.78,

    # More International
    "france24.com": 0.80,
    "cbc.ca": 0.84,
    "abc.net.au": 0.83,
    "euronews.com": 0.75,
    "scmp.com": 0.72,  # South China Morning Post
    "timesofindia.indiatimes.com": 0.68,
    "nhk.or.jp": 0.82,  # NHK World
    "rfi.fr": 0.78,

    # Aggregators / communities (lower — articles come from diverse underlying sources)
    "news.ycombinator.com": 0.65,  # Hacker News — links out, community filter applies

    # Partisan / lower reliability (still included but scored lower)
    "foxnews.com": 0.55,
    "msnbc.com": 0.60,
    "breitbart.com": 0.25,
    "dailymail.co.uk": 0.45,
    "nypost.com": 0.55,

    # Known unreliable / satire
    "theonion.com": 0.0,
    "babylonbee.com": 0.0,
    "naturalews.com": 0.05,
    "infowars.com": 0.05,
}

DEFAULT_RELIABILITY = 0.50  # Unknown sources get neutral score


def get_source_reliability(url: str) -> float:
    """Return reliability score for a given URL's domain."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return SOURCE_RELIABILITY.get(domain, DEFAULT_RELIABILITY)
    except Exception:
        return DEFAULT_RELIABILITY
