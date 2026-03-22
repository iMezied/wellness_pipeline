"""pipeline.py — المنسق الرئيسي"""

import os, time, schedule, traceback
from pathlib import Path
from datetime import datetime

from config import config
from db import init_db, get_next_topic, mark_topic_used, create_video_record, update_video, log_pipeline
from research import fetch_study
from script_generator import generate_script, build_full_script, build_caption
from media_generator import generate_voice, generate_video
from composer import generate_srt, compose_final_video, validate_video
from publisher import publish_tiktok, publish_instagram, publish_youtube, publish_pinterest, publish_snapchat, upload_to_r2


def run_single_video() -> bool:
    print(f"\n{'='*60}\n🚀 فيديو جديد — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'='*60}")
    topic = get_next_topic()
    if not topic:
        print("⚠️ لا مواضيع متبقية!"); return False

    video_id = create_video_record(topic["id"])
    log_pipeline(video_id, "init", f"موضوع: {topic['topic_ar']}")

    try:
        update_video(video_id, status="generating")

        study = fetch_study(topic["pubmed_keywords"])
        if not study: raise RuntimeError(f"لا دراسة لـ: {topic['topic_en']}")
        log_pipeline(video_id, "research", f"✅ {study.title[:80]}")
        update_video(video_id, pubmed_doi=study.doi, pubmed_title=study.title[:500])

        script = generate_script(topic["topic_ar"], study)
        full_text = build_full_script(script)
        caption = build_caption(script, study)
        duration_sec = int(script.get("duration_estimate_sec", 45))
        update_video(video_id, script_ar=full_text[:5000])

        audio_path = os.path.join(config.TEMP_DIR, f"audio_{video_id}.mp3")
        generate_voice(full_text, audio_path)
        update_video(video_id, audio_path=audio_path)
        log_pipeline(video_id, "voice", "✅ جاهز")

        raw_video_path = os.path.join(config.TEMP_DIR, f"video_raw_{video_id}.mp4")
        generate_video(topic["category"], duration_sec, raw_video_path)
        log_pipeline(video_id, "video", "✅ جاهز")

        update_video(video_id, status="composing")
        srt_content = generate_srt(audio_path)
        log_pipeline(video_id, "subtitles", "✅ جاهز")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = os.path.join(config.OUTPUT_DIR, topic["category"], f"video_{video_id}_{timestamp}.mp4")
        Path(final_path).parent.mkdir(parents=True, exist_ok=True)
        compose_final_video(raw_video_path, audio_path, srt_content, final_path, duration_sec)
        update_video(video_id, final_path=final_path)

        qc = validate_video(final_path)
        if not qc["valid"]: raise RuntimeError(f"QC فشل: {', '.join(qc['issues'])}")
        log_pipeline(video_id, "qc", f"✅ {qc['duration']:.1f}s | {qc['size_mb']}MB")

        public_url = upload_to_r2(final_path)
        log_pipeline(video_id, "cdn", f"✅ {public_url}")

        update_video(video_id, status="publishing")
        short_title = script.get("hook", topic["topic_ar"])[:100]
        results = {}

        platforms = [
            ("tiktok",    lambda: publish_tiktok(final_path, caption)),
            ("instagram", lambda: publish_instagram(final_path, caption, public_url)),
            ("youtube",   lambda: publish_youtube(final_path, short_title, caption)),
            ("pinterest", lambda: publish_pinterest(public_url, short_title, caption[:500])),
            ("snapchat",  lambda: publish_snapchat(final_path, caption[:250])),
        ]
        for name, fn in platforms:
            try:
                results[name] = fn()
                log_pipeline(video_id, "publish", f"✅ {name}: {results[name]}")
            except Exception as e:
                log_pipeline(video_id, "publish", f"❌ {name}: {e}", "error")
            time.sleep(3)

        update_video(video_id, status="done",
            tiktok_id=results.get("tiktok"), instagram_id=results.get("instagram"),
            youtube_id=results.get("youtube"), pinterest_id=results.get("pinterest"),
            snapchat_id=results.get("snapchat"), published_at=datetime.now())
        mark_topic_used(topic["id"])

        for p in [audio_path, raw_video_path]:
            try: os.remove(p)
            except: pass

        print(f"\n✅ فيديو #{video_id} على {len(results)}/5 منصات")
        return True

    except Exception as e:
        log_pipeline(video_id, "error", traceback.format_exc(), "error")
        update_video(video_id, status="failed", error_msg=str(e)[:500])
        print(f"\n❌ فيديو #{video_id} فشل: {e}")
        return False


def start_scheduler():
    schedule.every().day.at("05:00").do(run_single_video)
    schedule.every().day.at("11:00").do(run_single_video)
    schedule.every().day.at("17:00").do(run_single_video)
    print("🤖 Scheduler نشط — 05:00 | 11:00 | 17:00 UTC")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    import sys
    config.validate()
    init_db()
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        run_single_video()
    else:
        start_scheduler()
