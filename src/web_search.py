from io import BytesIO
from pathlib import Path

from PIL import Image
import requests

from .matcher import is_social_url


SERPAPI_IMAGE_URL = "https://serpapi.com/image"
SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
SERPAPI_MAX_IMAGE_BYTES = 500_000


def _image_for_upload(path: Path) -> tuple[str, str, bytes]:
    """Return an image payload that meets SerpApi's 500 KB upload limit."""
    raw = path.read_bytes()
    if len(raw) <= SERPAPI_MAX_IMAGE_BYTES:
        return path.name, "application/octet-stream", raw

    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((1600, 1600))

        for quality in (85, 75, 65, 55, 45):
            buffer = BytesIO()
            image.save(buffer, format="JPEG", optimize=True, quality=quality)
            payload = buffer.getvalue()
            if len(payload) <= SERPAPI_MAX_IMAGE_BYTES:
                return f"{path.stem}.jpg", "image/jpeg", payload

    raise RuntimeError("Could not compress the image below SerpApi's 500 KB limit.")


def upload_image(image_path: str | Path, api_key: str) -> str:
    path = Path(image_path)
    filename, content_type, payload = _image_for_upload(path)
    response = requests.post(
        SERPAPI_IMAGE_URL,
        files={"image": (filename, payload, content_type)},
        data={"api_key": api_key},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    if "image_id" not in payload:
        raise RuntimeError(f"SerpApi upload failed: {payload}")

    return payload["image_id"]


def google_lens_search(image_id: str, api_key: str,
                       search_type: str = "exact_matches") -> dict:
    params = {
        "engine": "google_lens",
        "image_id": image_id,
        "type": search_type,
        "api_key": api_key,
        "hl": "en",
        "country": "in",
        "safe": "active",
        "no_cache": "true",
    }

    response = requests.get(SERPAPI_SEARCH_URL, params=params, timeout=90)
    response.raise_for_status()
    payload = response.json()

    if "error" in payload:
        raise RuntimeError(payload["error"])

    return payload


def social_candidates(payload: dict) -> list[dict]:
    """Return unique Google Lens results that point to social-media domains."""
    preferred_keys = ("exact_matches", "visual_matches", "organic_results")
    candidates = []
    seen_urls = set()

    for key in preferred_keys:
        for item in payload.get(key, []) or []:
            link = item.get("link", "")
            if not link or link in seen_urls or not is_social_url(link):
                continue
            seen_urls.add(link)
            candidates.append(item)

    return candidates


def choose_candidate(payload: dict) -> dict | None:
    """Return the first dynamically discovered social-media candidate."""
    candidates = social_candidates(payload)
    return candidates[0] if candidates else None


def download_image(
    url: str, output_path: str | Path, timeout: int = 12
) -> bool:
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
            stream=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if not content_type.startswith("image/"):
            return False

        path = Path(output_path)
        with path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)

        return path.stat().st_size > 0
    except requests.RequestException:
        return False
