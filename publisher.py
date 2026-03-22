import requests
import time
from pathlib import Path
from config import config

# ─── TIKTOK ──────────────────────────────────────────────────────────────────

def publish_tiktok(video_path: str, caption: str) -> str:
    """ينشر على TikTok عبر Content Posting API"""

    file_size = Path(video_path).stat().st_size

    # المرحلة 1: init upload
    init_resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {config.TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json; charset=UTF-8"
        },
        json={
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1
            }
        },
        timeout=30
    )
    init_resp.raise_for_status()
    data = init_resp.json()["data"]
    upload_url = data["upload_url"]
    publish_id = data["publish_id"]

    # المرحلة 2: رفع الملف
    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{file_size-1}/{file_size}",
            "Content-Length": str(file_size)
        },
        data=video_data,
        timeout=120
    )
    upload_resp.raise_for_status()

    return publish_id

# ─── INSTAGRAM ───────────────────────────────────────────────────────────────

def publish_instagram(video_path: str, caption: str, video_url: str) -> str:
    """
    ينشر Instagram Reel.
    ملاحظة: Instagram Graph API يحتاج URL عام للفيديو (مش local path)
    → ترفع الفيديو على S3/Cloudflare R2 أولاً وتعطيه الـ URL
    """
    base = "https://graph.facebook.com/v19.0"
    acc = config.INSTAGRAM_ACCOUNT_ID
    token = config.INSTAGRAM_ACCESS_TOKEN

    # المرحلة 1: إنشاء media container
    container_resp = requests.post(
        f"{base}/{acc}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
        timeout=30
    )
    container_resp.raise_for_status()
    container_id = container_resp.json()["id"]

    # انتظار processing
    _wait_instagram_container(container_id, token, base)

    # المرحلة 2: نشر
    publish_resp = requests.post(
        f"{base}/{acc}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": token,
        },
        timeout=30
    )
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]

def _wait_instagram_container(container_id: str, token: str, base: str, max_wait: int = 180):
    for _ in range(max_wait // 10):
        time.sleep(10)
        resp = requests.get(
            f"{base}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=15
        ).json()
        status = resp.get("status_code", "")
        if status == "FINISHED":
            return
        elif status == "ERROR":
            raise RuntimeError(f"Instagram container error: {resp.get('status')}")
    raise TimeoutError("Instagram container timed out")

# ─── YOUTUBE SHORTS ──────────────────────────────────────────────────────────

def publish_youtube(video_path: str, title: str, description: str) -> str:
    """ينشر YouTube Short عبر YouTube Data API v3"""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    import json

    creds_data = json.loads(config.YOUTUBE_CLIENT_SECRET)
    creds = Credentials(
        token=creds_data["token"],
        refresh_token=creds_data["refresh_token"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        token_uri="https://oauth2.googleapis.com/token"
    )

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": ["صحة", "wellness", "تغذية", "دراسات"],
            "categoryId": "26",  # Howto & Style
            "defaultLanguage": "ar",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    return response["id"]

# ─── PINTEREST ────────────────────────────────────────────────────────────────

def publish_pinterest(video_url: str, title: str, description: str) -> str:
    """ينشر Pinterest Idea Pin"""
    resp = requests.post(
        "https://api.pinterest.com/v5/pins",
        headers={
            "Authorization": f"Bearer {config.PINTEREST_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "board_id": config.PINTEREST_BOARD_ID,
            "title": title[:100],
            "description": description[:500],
            "media_source": {
                "source_type": "video_url",
                "url": video_url,
            }
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()["id"]

# ─── SNAPCHAT SPOTLIGHT ───────────────────────────────────────────────────────

def publish_snapchat(video_path: str, caption: str) -> str:
    """ينشر Snapchat Spotlight"""
    file_size = Path(video_path).stat().st_size

    # رفع الفيديو
    with open(video_path, "rb") as f:
        upload_resp = requests.post(
            "https://adsapi.snapchat.com/v1/media",
            headers={"Authorization": f"Bearer {config.SNAPCHAT_ACCESS_TOKEN}"},
            files={"file": ("video.mp4", f, "video/mp4")},
            data={"name": caption[:50]},
            timeout=120
        )
    upload_resp.raise_for_status()
    media_id = upload_resp.json()["media"][0]["id"]

    # نشر كـ Spotlight
    publish_resp = requests.post(
        "https://adsapi.snapchat.com/v1/spotlight",
        headers={
            "Authorization": f"Bearer {config.SNAPCHAT_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "spotlight": [{
                "media_id": media_id,
                "caption_body": caption[:250],
            }]
        },
        timeout=30
    )
    publish_resp.raise_for_status()
    return media_id

# ─── UPLOAD TO CDN (مطلوب لـ Instagram وPinterest) ───────────────────────────

def upload_to_r2(video_path: str) -> str:
    """
    يرفع الفيديو على Cloudflare R2 ويرجع URL عام.
    يحتاج: pip install boto3
    وضع مفاتيح R2 في .env
    """
    import boto3
    from botocore.config import Config as BotoConfig

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
        config=BotoConfig(signature_version="s3v4"),
    )

    filename = Path(video_path).name
    bucket = os.getenv("R2_BUCKET", "wellness-videos")

    s3.upload_file(
        video_path, bucket, filename,
        ExtraArgs={"ContentType": "video/mp4", "ACL": "public-read"}
    )

    return f"https://{os.getenv('R2_PUBLIC_DOMAIN')}/{filename}"

import os
