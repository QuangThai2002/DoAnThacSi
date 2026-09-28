"""Optional, consent-based connectors for market signals.

Nothing in this module scrapes Shopee or social platforms.  Every request is
made only after the owner supplies the platform credential required by that
platform, and every response keeps its platform label and timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

import requests


REQUEST_TIMEOUT_SECONDS = 12


def _empty_result(platform: str, message: str) -> dict[str, object]:
    return {"platform": platform, "status": "Chưa kết nối", "message": message, "items": []}


def _error_result(platform: str) -> dict[str, object]:
    return {
        "platform": platform,
        "status": "Không thể làm mới",
        "message": "Nền tảng không trả dữ liệu. Hãy kiểm tra quyền, token và cấu hình kết nối.",
        "items": [],
    }


def _live_result(platform: str, items: list[dict[str, str]]) -> dict[str, object]:
    return {
        "platform": platform,
        "status": "Đã kết nối",
        "message": f"Dữ liệu làm mới lúc {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        "items": items,
    }


def fetch_youtube_brief(query: str, api_key: str) -> dict[str, object]:
    """Fetch public YouTube search results for a market keyword."""
    if not api_key:
        return _empty_result("YouTube", "Thiếu YOUTUBE_API_KEY trong secrets.")
    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "order": "date",
                "maxResults": 6,
                "regionCode": "VN",
                "relevanceLanguage": "vi",
                "key": api_key,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = []
        for item in response.json().get("items", []):
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            if not video_id:
                continue
            items.append(
                {
                    "title": str(snippet.get("title", "Video không có tiêu đề")),
                    "creator": str(snippet.get("channelTitle", "Không rõ kênh")),
                    "published_at": str(snippet.get("publishedAt", ""))[:10],
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )
        return _live_result("YouTube", items)
    except (requests.RequestException, ValueError, TypeError):
        return _error_result("YouTube")


def fetch_facebook_page_brief(page_id: str, access_token: str) -> dict[str, object]:
    """Fetch posts from the owner-authorized Facebook Page only."""
    if not page_id or not access_token:
        return _empty_result("Facebook", "Cần META_PAGE_ID và META_PAGE_ACCESS_TOKEN trong secrets.")
    try:
        response = requests.get(
            f"https://graph.facebook.com/v24.0/{page_id}/posts",
            params={
                "fields": "message,created_time,permalink_url",
                "limit": 6,
                "access_token": access_token,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = []
        for item in response.json().get("data", []):
            message = " ".join(str(item.get("message", "Bài viết không có nội dung")).split())
            items.append(
                {
                    "title": message[:110] + ("…" if len(message) > 110 else ""),
                    "creator": "Facebook Page đã cấp quyền",
                    "published_at": str(item.get("created_time", ""))[:10],
                    "url": str(item.get("permalink_url", "")),
                }
            )
        return _live_result("Facebook", items)
    except (requests.RequestException, ValueError, TypeError):
        return _error_result("Facebook")


def fetch_tiktok_research_brief(query: str, client_key: str, client_secret: str) -> dict[str, object]:
    """Fetch TikTok Research API data when an approved research client exists."""
    if not client_key or not client_secret:
        return _empty_result(
            "TikTok",
            "Cần TIKTOK_RESEARCH_CLIENT_KEY và TIKTOK_RESEARCH_CLIENT_SECRET của dự án đã được duyệt.",
        )
    try:
        token_response = requests.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={"client_key": client_key, "client_secret": client_secret, "grant_type": "client_credentials"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        token_response.raise_for_status()
        token = str(token_response.json().get("access_token", ""))
        if not token:
            return _error_result("TikTok")
        response = requests.post(
            "https://open.tiktokapis.com/v2/research/video/query/?fields=id,video_description,create_time,view_count,like_count,hashtag_names",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "query": {"and": [{"operation": "EQ", "field_name": "keyword", "field_values": [query]}]},
                "max_count": 6,
                "cursor": 0,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = []
        for item in response.json().get("data", {}).get("videos", []):
            description = " ".join(str(item.get("video_description", "Video TikTok")).split())
            items.append(
                {
                    "title": description[:110] + ("…" if len(description) > 110 else ""),
                    "creator": f"{int(item.get('view_count', 0)):,} lượt xem · {int(item.get('like_count', 0)):,} lượt thích",
                    "published_at": str(item.get("create_time", ""))[:10],
                    "url": "",
                }
            )
        return _live_result("TikTok", items)
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return _error_result("TikTok")


def fetch_configured_sources(query: str, credentials: Mapping[str, str]) -> list[dict[str, object]]:
    """Call only sources for which the owner deliberately configured credentials."""
    return [
        fetch_youtube_brief(query, str(credentials.get("YOUTUBE_API_KEY", ""))),
        fetch_facebook_page_brief(
            str(credentials.get("META_PAGE_ID", "")),
            str(credentials.get("META_PAGE_ACCESS_TOKEN", "")),
        ),
        fetch_tiktok_research_brief(
            query,
            str(credentials.get("TIKTOK_RESEARCH_CLIENT_KEY", "")),
            str(credentials.get("TIKTOK_RESEARCH_CLIENT_SECRET", "")),
        ),
    ]
