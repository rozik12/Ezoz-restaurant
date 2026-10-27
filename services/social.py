"""Cross-posting to Instagram, Facebook (Meta Graph API) and YouTube Shorts (YouTube Data API v3).

Each publisher returns a PublishResult and never raises, so one failing platform cannot block the others.
A platform with missing credentials reports "not configured" instead of failing silently.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

import aiohttp

from config import settings

log = logging.getLogger(__name__)

PLATFORMS: dict[str, str] = {"ig": "Instagram", "fb": "Facebook", "yt": "YouTube Shorts"}
VIDEO_ONLY = {"yt"}          # YouTube Shorts needs a video
IG_CAPTION_LIMIT = 2200


@dataclass
class LocalMedia:
    path: Path
    kind: str                # "photo" | "video"


@dataclass
class PublishResult:
    platform: str
    ok: bool
    detail: str              # link or id on success, reason on failure


class NotConfigured(Exception):
    pass


class PublishError(Exception):
    pass


# --------------------------------------------------------------------------------------
# Public hosting for Meta
# --------------------------------------------------------------------------------------
def expose_publicly(media: LocalMedia) -> tuple[str, Path]:
    """Meta's servers DOWNLOAD the media from a public HTTPS URL, so the file must be reachable.

    This copies it into MEDIA_DIR, which your web server (nginx, Caddy, S3 sync, ...) must serve at
    PUBLIC_MEDIA_BASE_URL. Never pass Telegram's own file URL to Meta: it contains the bot token.
    Swap this function for an S3/R2 upload if you prefer object storage.
    """
    if not settings.public_media_base_url:
        raise NotConfigured("PUBLIC_MEDIA_BASE_URL is not set")
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{media.path.suffix}"
    target = settings.media_dir / name
    shutil.copyfile(media.path, target)
    return f"{settings.public_media_base_url}/{name}", target


async def _graph(session: aiohttp.ClientSession, method: str, path: str, token: str, **params) -> dict:
    url = f"https://graph.facebook.com/{settings.graph_version}/{path}"
    params["access_token"] = token
    async with session.request(method, url, params=params, timeout=aiohttp.ClientTimeout(total=120)) as r:
        data = await r.json(content_type=None)
        if r.status >= 400 or "error" in data:
            raise PublishError(data.get("error", {}).get("message", f"HTTP {r.status}"))
        return data


# --------------------------------------------------------------------------------------
# Instagram (Graph API: create container -> wait -> media_publish)
# --------------------------------------------------------------------------------------
async def publish_instagram(media: LocalMedia, caption: str) -> PublishResult:
    name = PLATFORMS["ig"]
    try:
        if not (settings.ig_user_id and settings.meta_access_token):
            raise NotConfigured("IG_USER_ID / META_ACCESS_TOKEN not set")
        url, hosted = expose_publicly(media)
        tok, uid = settings.meta_access_token, settings.ig_user_id
        async with aiohttp.ClientSession() as s:
            if media.kind == "photo":
                c = await _graph(s, "POST", f"{uid}/media", tok, image_url=url, caption=caption[:IG_CAPTION_LIMIT])
            else:
                c = await _graph(s, "POST", f"{uid}/media", tok, media_type="REELS", video_url=url,
                                 caption=caption[:IG_CAPTION_LIMIT], share_to_feed="true")
            container = c["id"]
            for _ in range(60):          # video containers are processed asynchronously (max ~5 min)
                st = await _graph(s, "GET", container, tok, fields="status_code")
                if st.get("status_code") == "FINISHED":
                    break
                if st.get("status_code") in ("ERROR", "EXPIRED"):
                    raise PublishError(f"Instagram processing failed: {st}")
                await asyncio.sleep(5)
            else:
                raise PublishError("Instagram processing timed out")
            pub = await _graph(s, "POST", f"{uid}/media_publish", tok, creation_id=container)
            info = await _graph(s, "GET", pub["id"], tok, fields="permalink")
        hosted.unlink(missing_ok=True)
        return PublishResult(name, True, info.get("permalink", pub["id"]))
    except NotConfigured as e:
        return PublishResult(name, False, f"not configured ({e})")
    except Exception as e:
        log.exception("Instagram publish failed")
        return PublishResult(name, False, str(e))


# --------------------------------------------------------------------------------------
# Facebook Page
# --------------------------------------------------------------------------------------
async def publish_facebook(media: LocalMedia, caption: str) -> PublishResult:
    name = PLATFORMS["fb"]
    try:
        if not (settings.fb_page_id and settings.fb_page_token):
            raise NotConfigured("FB_PAGE_ID / FB_PAGE_TOKEN not set")
        url, hosted = expose_publicly(media)
        async with aiohttp.ClientSession() as s:
            if media.kind == "photo":
                r = await _graph(s, "POST", f"{settings.fb_page_id}/photos", settings.fb_page_token,
                                 url=url, caption=caption)
            else:
                r = await _graph(s, "POST", f"{settings.fb_page_id}/videos", settings.fb_page_token,
                                 file_url=url, description=caption)
        hosted.unlink(missing_ok=True)
        return PublishResult(name, True, f"https://facebook.com/{r.get('post_id') or r['id']}")
    except NotConfigured as e:
        return PublishResult(name, False, f"not configured ({e})")
    except Exception as e:
        log.exception("Facebook publish failed")
        return PublishResult(name, False, str(e))


# --------------------------------------------------------------------------------------
# YouTube Shorts (Data API v3, resumable upload; vertical video up to the current Shorts length limit)
# --------------------------------------------------------------------------------------
def _upload_youtube_sync(path: Path, title: str, description: str) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        None,
        refresh_token=settings.yt_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.yt_client_id,
        client_secret=settings.yt_client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {"title": title[:100], "description": description, "categoryId": "22"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(path), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return f"https://youtube.com/shorts/{resp['id']}"


async def publish_youtube(media: LocalMedia, caption: str) -> PublishResult:
    name = PLATFORMS["yt"]
    try:
        if media.kind != "video":
            raise PublishError("YouTube Shorts needs a video")
        if not (settings.yt_client_id and settings.yt_client_secret and settings.yt_refresh_token):
            raise NotConfigured("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN not set")
        first_line = (caption.strip().splitlines() or ["E'zoz Tashkent"])[0]
        title = f"{first_line[:88]} #Shorts"
        link = await asyncio.to_thread(_upload_youtube_sync, media.path, title, f"{caption}\n\n#Shorts")
        return PublishResult(name, True, link)
    except NotConfigured as e:
        return PublishResult(name, False, f"not configured ({e})")
    except Exception as e:
        log.exception("YouTube publish failed")
        return PublishResult(name, False, str(e))


_PUBLISHERS: dict[str, Callable[[LocalMedia, str], Awaitable[PublishResult]]] = {
    "ig": publish_instagram,
    "fb": publish_facebook,
    "yt": publish_youtube,
}


async def publish_all(targets: list[str], media: LocalMedia, caption: str) -> list[PublishResult]:
    return list(await asyncio.gather(*(_PUBLISHERS[t](media, caption) for t in targets)))
