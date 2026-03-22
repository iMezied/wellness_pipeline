import subprocess
import requests
import time
import os
import json
from pathlib import Path
from config import config

# ─── SUBTITLES (AssemblyAI) ───────────────────────────────────────────────────

def generate_srt(audio_path: str) -> str:
    """يولد ملف SRT من الملف الصوتي"""

    headers = {"authorization": config.ASSEMBLY_API_KEY}

    # رفع الملف
    with open(audio_path, "rb") as f:
        upload_resp = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=f,
            timeout=60
        )
    upload_url = upload_resp.json()["upload_url"]

    # طلب التحويل
    transcript_resp = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=headers,
        json={
            "audio_url": upload_url,
            "language_code": "ar",
            "punctuate": True,
        },
        timeout=30
    )
    transcript_id = transcript_resp.json()["id"]

    # انتظار
    for _ in range(40):
        time.sleep(5)
        poll = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers,
            timeout=15
        ).json()
        if poll["status"] == "completed":
            break
        elif poll["status"] == "error":
            raise RuntimeError(f"AssemblyAI error: {poll.get('error')}")

    # جلب SRT
    srt_resp = requests.get(
        f"https://api.assemblyai.com/v2/transcript/{transcript_id}/srt",
        headers=headers,
        timeout=15
    )
    return srt_resp.text

# ─── VIDEO COMPOSER (FFmpeg) ──────────────────────────────────────────────────

def compose_final_video(
    video_path: str,
    audio_path: str,
    srt_content: str,
    output_path: str,
    video_duration: int,
) -> str:
    """
    يدمج الفيديو + الصوت + الترجمة + يضيف watermark البراند
    الناتج: فيديو 1080x1920 جاهز للنشر
    """

    temp_dir = Path(config.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    srt_path = str(temp_dir / f"{Path(output_path).stem}.srt")
    looped_video = str(temp_dir / f"{Path(output_path).stem}_looped.mp4")

    # حفظ ملف SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    # المرحلة 1: تكرار الفيديو بما يكفي لتغطية مدة الصوت
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,
        "-t", str(video_duration + 2),
        "-c:v", "libx264",
        "-preset", "fast",
        "-an",  # بدون صوت
        looped_video
    ])

    # المرحلة 2: دمج الصوت + الفيديو + الترجمة + البراند
    subtitle_style = (
        "FontName=Arial,"
        "FontSize=20,"
        "PrimaryColour=&H00FFFFFF,"  # أبيض
        "OutlineColour=&H00000000,"  # حدود سوداء
        "BorderStyle=3,"
        "Outline=2,"
        "Shadow=1,"
        "Alignment=2,"              # وسط أسفل
        "MarginV=80"                # هامش من الأسفل
    )

    # escape مسار SRT للـ FFmpeg
    srt_escaped = srt_path.replace(":", "\\:").replace("'", "\\'")

    _run_ffmpeg([
        "ffmpeg", "-y",
        "-i", looped_video,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"subtitles='{srt_escaped}':force_style='{subtitle_style}',"
        f"drawtext=text='{config.BRAND_NAME}':fontcolor=white:fontsize=28:"
        f"x=(w-text_w)/2:y=80:alpha=0.7[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(min(video_duration, config.MAX_DURATION_SEC)),
        "-movflags", "+faststart",
        output_path
    ])

    # تنظيف الملفات المؤقتة
    for f in [srt_path, looped_video]:
        try:
            os.remove(f)
        except Exception:
            pass

    return output_path

def _run_ffmpeg(cmd: list):
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-1000:]}")

def validate_video(video_path: str) -> dict:
    """يتحقق من صحة الفيديو قبل النشر"""
    probe = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        video_path
    ], capture_output=True, text=True, timeout=30)

    data = json.loads(probe.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = next((s for s in streams if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in streams if s["codec_type"] == "audio"), None)

    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / 1_000_000

    issues = []
    if duration < 5:
        issues.append(f"Duration too short: {duration:.1f}s")
    if duration > 60:
        issues.append(f"Duration too long: {duration:.1f}s")
    if size_mb > 300:
        issues.append(f"File too large: {size_mb:.1f}MB")
    if not audio_stream:
        issues.append("No audio stream")
    if not video_stream:
        issues.append("No video stream")

    return {
        "valid": len(issues) == 0,
        "duration": duration,
        "size_mb": round(size_mb, 2),
        "issues": issues,
    }
