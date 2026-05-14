import asyncio
from datetime import datetime

import feedparser
import httpx

from app.agents.state import SourceItem
from app.core.logging import get_logger

logger = get_logger(__name__)

RSS_FEEDS = [
    # Wire services
    ("Reuters", "https://feeds.reuters.com/reuters/topNews"),
    ("AP News", "https://feeds.apnews.com/rss/apf-topnews"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),

    # US news
    ("NPR", "https://feeds.npr.org/1001/rss.xml"),
    ("NY Times", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
    ("Washington Post", "https://feeds.washingtonpost.com/rss/world"),
    ("Guardian", "https://www.theguardian.com/world/rss"),
    ("USA Today", "https://rssfeeds.usatoday.com/usatoday-NewsTopStories"),
    ("PBS NewsHour", "https://www.pbs.org/newshour/feeds/rss/headlines"),
    ("NBC News", "https://feeds.nbcnews.com/nbcnews/public/news"),
    ("CBS News", "https://www.cbsnews.com/latest/rss/main"),
    ("LA Times", "https://www.latimes.com/world-nation/rss2.0.xml"),

    # Business / finance
    ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Financial Times", "https://www.ft.com/rss/home/uk"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("Forbes", "https://www.forbes.com/real-time/feed2/"),
    ("Wall Street Journal", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("The Economist", "https://www.economist.com/rss/news_rss.xml"),

    # Tech
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),

    # Politics
    ("Politico", "https://rss.politico.com/politics-news.xml"),
    ("The Hill", "https://thehill.com/news/feed/"),

    # Science / Health
    ("Science Daily", "https://www.sciencedaily.com/rss/all.xml"),
    ("Nature News", "https://www.nature.com/nature.rss"),
    ("New Scientist", "https://www.newscientist.com/feed/home"),
    ("Live Science", "https://www.livescience.com/feeds/all"),

    # Environment
    ("Guardian Environment", "https://www.theguardian.com/environment/rss"),
    ("Inside Climate News", "https://insideclimatenews.org/feed/"),

    # International
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Deutsche Welle", "https://rss.dw.com/rdf/rss-en-all"),
    ("France24", "https://www.france24.com/en/rss"),
    ("CBC Canada", "https://www.cbc.ca/cmlink/rss-world"),
    ("ABC Australia", "https://www.abc.net.au/news/feed/51120/rss.xml"),
    ("Euronews", "https://www.euronews.com/rss?format=mrss&level=theme&name=news"),
    ("South China Morning Post", "https://www.scmp.com/rss/91/feed"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
    ("NHK World", "https://www3.nhk.or.jp/rss/news/cat0.xml"),
    ("RFI English", "https://en.rfi.fr/rss"),
]


async def fetch_rss_feed(
    client: httpx.AsyncClient,
    name: str,
    url: str,
    query_keywords: list[str],
) -> list[SourceItem]:
    try:
        response = await client.get(url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        feed = feedparser.parse(response.text)

        items: list[SourceItem] = []
        keywords_lower = [k.lower() for k in query_keywords]

        for entry in feed.entries[:30]:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            combined = f"{title} {summary}".lower()

            # Simple keyword relevance filter
            if not any(kw in combined for kw in keywords_lower):
                continue

            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except Exception:
                    pass

            items.append({
                "url": entry.get("link", ""),
                "title": title,
                "source_name": name,
                "published_at": published,
                "raw_text": summary[:2000],
                "feed_origin": "rss",
            })

        return items

    except Exception as exc:
        logger.warning("rss_feed_error", feed=name, url=url, error=str(exc))
        return []


async def fetch_all_rss(query: str, max_per_feed: int = 10) -> list[SourceItem]:
    keywords = query.lower().split()[:5]

    async with httpx.AsyncClient(headers={"User-Agent": "NewsroomBot/1.0"}) as client:
        tasks = [
            fetch_rss_feed(client, name, url, keywords)
            for name, url in RSS_FEEDS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[SourceItem] = []
    for result in results:
        if isinstance(result, list):
            all_items.extend(result)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[SourceItem] = []
    for item in all_items:
        if item["url"] and item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique.append(item)

    return unique
