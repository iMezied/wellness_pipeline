import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """Parses common boolean env values like true/false, 1/0, yes/no."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

@dataclass
class Config:
    BRAND_NAME: str              = os.getenv("BRAND_NAME", "Mujarbat")
    DISCLAIMER_AR: str           = os.getenv("DISCLAIMER_AR", "المحتوى مبني على دراسات موثقة. استشر طبيبك.")
    CLAUDE_API_KEY: str          = os.getenv("CLAUDE_API_KEY", "")
    ELEVENLABS_API_KEY: str      = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str     = os.getenv("ELEVENLABS_VOICE_ID", "")
    KLING_API_KEY: str           = os.getenv("KLING_API_KEY", "")
    ASSEMBLY_API_KEY: str        = os.getenv("ASSEMBLY_API_KEY", "")
    TIKTOK_ACCESS_TOKEN: str     = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    INSTAGRAM_ACCESS_TOKEN: str  = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_ACCOUNT_ID: str    = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
    YOUTUBE_CLIENT_SECRET: str   = os.getenv("YOUTUBE_CLIENT_SECRET", "{}")
    PINTEREST_ACCESS_TOKEN: str  = os.getenv("PINTEREST_ACCESS_TOKEN", "")
    PINTEREST_BOARD_ID: str      = os.getenv("PINTEREST_BOARD_ID", "")
    SNAPCHAT_ACCESS_TOKEN: str   = os.getenv("SNAPCHAT_ACCESS_TOKEN", "")
    DB_HOST: str                 = os.getenv("DB_HOST", "db")
    DB_PORT: int                 = int(os.getenv("DB_PORT", "3306"))
    DB_NAME: str                 = os.getenv("DB_NAME", "wellness_pipeline")
    DB_USER: str                 = os.getenv("DB_USER", "wellness_user")
    DB_PASS: str                 = os.getenv("DB_PASS", "")
    REDIS_URL: str               = os.getenv("REDIS_URL", "redis://redis:6379")
    R2_ACCOUNT_ID: str           = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY: str           = os.getenv("R2_ACCESS_KEY", "")
    R2_SECRET_KEY: str           = os.getenv("R2_SECRET_KEY", "")
    R2_BUCKET: str               = os.getenv("R2_BUCKET", "wellness-videos")
    R2_PUBLIC_DOMAIN: str        = os.getenv("R2_PUBLIC_DOMAIN", "")
    OUTPUT_DIR: str              = os.getenv("OUTPUT_DIR", "/var/wellness/output")
    TEMP_DIR: str                = os.getenv("TEMP_DIR", "/var/wellness/tmp")
    VIDEO_WIDTH: int             = 1080
    VIDEO_HEIGHT: int            = 1920
    VIDEO_FPS: int               = 30
    MAX_DURATION_SEC: int        = 60

    def is_tiktok_enabled(self) -> bool:
        auto = bool(self.TIKTOK_ACCESS_TOKEN)
        return _env_bool("TIKTOK_ENABLED", auto)

    def is_instagram_enabled(self) -> bool:
        auto = bool(self.INSTAGRAM_ACCESS_TOKEN and self.INSTAGRAM_ACCOUNT_ID)
        return _env_bool("INSTAGRAM_ENABLED", auto)

    def is_youtube_enabled(self) -> bool:
        # Keep parsing minimal here to avoid startup failure on malformed JSON.
        secret = (self.YOUTUBE_CLIENT_SECRET or "").strip()
        auto = secret not in {"", "{}"}
        return _env_bool("YOUTUBE_ENABLED", auto)

    def is_pinterest_enabled(self) -> bool:
        auto = bool(self.PINTEREST_ACCESS_TOKEN and self.PINTEREST_BOARD_ID)
        return _env_bool("PINTEREST_ENABLED", auto)

    def is_snapchat_enabled(self) -> bool:
        auto = bool(self.SNAPCHAT_ACCESS_TOKEN)
        return _env_bool("SNAPCHAT_ENABLED", auto)

    def enabled_social_platforms(self) -> list[str]:
        enabled = []
        if self.is_tiktok_enabled():
            enabled.append("tiktok")
        if self.is_instagram_enabled():
            enabled.append("instagram")
        if self.is_youtube_enabled():
            enabled.append("youtube")
        if self.is_pinterest_enabled():
            enabled.append("pinterest")
        if self.is_snapchat_enabled():
            enabled.append("snapchat")
        return enabled

    def requires_public_video_url(self) -> bool:
        # Instagram and Pinterest publish endpoints consume a public URL.
        return self.is_instagram_enabled() or self.is_pinterest_enabled()

    def validate(self):
        required = {
            "CLAUDE_API_KEY": self.CLAUDE_API_KEY,
            "ELEVENLABS_API_KEY": self.ELEVENLABS_API_KEY,
            "KLING_API_KEY": self.KLING_API_KEY,
            "ASSEMBLY_API_KEY": self.ASSEMBLY_API_KEY,
            "DB_PASS": self.DB_PASS,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise EnvironmentError(
                "❌ مفاتيح مفقودة في .env:\n  " + "\n  ".join(missing)
            )
        print("✅ Config validated")

config = Config()
