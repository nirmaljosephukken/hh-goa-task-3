from src.matcher import is_social_url
from src.web_search import choose_candidate, social_candidates


def test_social_candidates_only_returns_social_media_urls():
    payload = {
        "exact_matches": [
            {"link": "https://news.example.com/story"},
            {"link": "https://www.instagram.com/p/matching-post/"},
        ],
        "visual_matches": [
            {"link": "https://x.com/example/status/1"},
        ],
    }

    candidates = social_candidates(payload)

    assert [candidate["link"] for candidate in candidates] == [
        "https://www.instagram.com/p/matching-post/",
        "https://x.com/example/status/1",
    ]
    assert choose_candidate(payload) == candidates[0]


def test_social_candidates_rejects_non_social_results():
    payload = {"exact_matches": [{"link": "https://example.com/photo"}]}

    assert social_candidates(payload) == []
    assert choose_candidate(payload) is None


def test_social_url_requires_an_actual_social_domain():
    assert is_social_url("https://instagram.com/p/matching-post/")
    assert is_social_url("https://www.threads.net/@example/post/example")
    assert is_social_url("https://www.pinterest.com/pin/example/")
    assert not is_social_url("https://m.youtube.com/watch?v=example")
    assert not is_social_url("https://notinstagram.com/p/matching-post/")
    assert not is_social_url("https://instagram.com.example.com/p/matching-post/")
