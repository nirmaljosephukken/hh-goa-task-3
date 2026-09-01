from urllib.parse import urlparse


SOCIAL_DOMAINS = (
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
    "reddit.com",
)


def is_social_url(url: str) -> bool:
    host = urlparse(url).hostname
    if not host:
        return False

    normalized_host = host.lower()
    return any(
        normalized_host == domain or normalized_host.endswith(f".{domain}")
        for domain in SOCIAL_DOMAINS
    )


def format_candidate(candidate: dict) -> str:
    title = candidate.get("title", "Untitled")
    source = candidate.get("source", "Unknown source")
    link = candidate.get("link", "")
    return f"{title} | {source} | {link}"
