import requests
import time
import os
from pathlib import Path
from config import config

# ─── VOICE GENERATION (ElevenLabs) ──────────────────────────────────────────

def generate_voice(text: str, output_path: str) -> str:
    """يولد ملف صوتي عربي من النص ويحفظه كـ MP3"""

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"

    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.75,          # ثبات الصوت
            "similarity_boost": 0.85,   # وضوح الصوت
            "style": 0.3,               # تعبيرية معتدلة
            "use_speaker_boost": True
        }
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    return output_path

# ─── VIDEO GENERATION (Kling AI) ─────────────────────────────────────────────

KLING_BASE = "https://api.kling.ai/v1"

WELLNESS_PROMPTS = {
    "nutrition": "Serene nature scene with fresh vegetables, olive oil, sunlight filtering through kitchen window, clean minimalist aesthetic, warm tones, 4K cinematic",
    "fitness": "Person doing gentle morning stretches outdoors, golden hour light, peaceful park, motivational atmosphere, clean modern style",
    "sleep": "Tranquil bedroom at night, moonlight, calm blue tones, peaceful sleeping scene, minimalist and relaxing",
    "mental": "Calm meditation scene, soft morning light, nature sounds implied, peaceful expression, warm muted colors",
    "longevity": "Healthy active person in nature, vibrant colors, sunlight, fresh air, energy and vitality visual",
    "herbs": "Close-up of fresh herbs and spices, olive oil, natural ingredients on wooden surface, warm Mediterranean tones",
}

def generate_video(category: str, duration: int, output_path: str) -> str:
    """يولد فيديو AI عبر Kling API"""

    prompt = WELLNESS_PROMPTS.get(category, WELLNESS_PROMPTS["nutrition"])

    # إنشاء طلب التوليد
    resp = requests.post(
        f"{KLING_BASE}/videos/text2video",
        headers={
            "Authorization": f"Bearer {config.KLING_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "prompt": prompt,
            "negative_prompt": "text, watermark, logo, people faces, violence, unhealthy food",
            "duration": min(duration, 10),  # Kling max per segment = 10s
            "aspect_ratio": "9:16",         # vertical للموبايل
            "cfg_scale": 0.5,
            "mode": "std",                   # std أرخص، pro أفضل جودة
        },
        timeout=30
    )
    resp.raise_for_status()
    task_id = resp.json()["data"]["task_id"]

    # انتظار الاكتمال
    video_url = _poll_kling_task(task_id)

    # تحميل الفيديو
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    video_resp = requests.get(video_url, timeout=120)
    video_resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(video_resp.content)

    return output_path

def _poll_kling_task(task_id: str, max_wait: int = 300) -> str:
    """ينتظر اكتمال مهمة Kling ويرجع رابط الفيديو"""
    elapsed = 0
    while elapsed < max_wait:
        resp = requests.get(
            f"{KLING_BASE}/videos/text2video/{task_id}",
            headers={"Authorization": f"Bearer {config.KLING_API_KEY}"},
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data.get("task_status")

        if status == "succeed":
            return data["task_result"]["videos"][0]["url"]
        elif status == "failed":
            raise RuntimeError(f"Kling task failed: {data.get('task_status_msg')}")

        time.sleep(15)
        elapsed += 15

    raise TimeoutError(f"Kling task {task_id} timed out after {max_wait}s")
