"""CKB Video Tool - Railway config"""
import os

CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL   = "claude-sonnet-5"

FFMPEG_PATH  = os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE_PATH = os.environ.get("FFPROBE_PATH", "ffprobe")

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR      = os.path.join(BASE_DIR, "input")
OUTPUT_DIR     = os.path.join(BASE_DIR, "output")
MUSIC_DIR      = os.path.join(BASE_DIR, "music")
ASSETS_DIR     = os.path.join(BASE_DIR, "assets")
DATABASE_DIR   = os.path.join(BASE_DIR, "database")
PROMPTS_DIR    = os.path.join(BASE_DIR, "prompts")
CONTENT_DB     = os.path.join(BASE_DIR, "content_db", "content.db")
THUMBNAILS_DIR = os.path.join(BASE_DIR, "thumbnails")
CAPTIONS_DIR   = os.path.join(BASE_DIR, "captions")
TEMP_DIR       = os.path.join(BASE_DIR, "temp")

VIDEO_WIDTH    = 1080
VIDEO_HEIGHT   = 1920
FONT_SIZE      = 38
LOGO_WIDTH     = 120
LOGO_HEIGHT    = 60
MUSIC_VOLUME   = 0.3

WHISPER_MODEL  = os.environ.get("WHISPER_MODEL", "small")
WHISPER_LANG   = os.environ.get("WHISPER_LANG", "vi")

SHOP_NAME     = os.environ.get("SHOP_NAME", "Cong Khang Bike")
SHOP_ADDRESS  = os.environ.get("SHOP_ADDRESS", "496 Dong Hai, Hai Phong")
SHOP_HOTLINE  = os.environ.get("SHOP_HOTLINE", "0762030888")
SHOP_ZALO     = os.environ.get("SHOP_ZALO", "0762030888")
SHOP_TIKTOK   = os.environ.get("SHOP_TIKTOK", "@xediencongkhang")
SHOP_YOUTUBE  = os.environ.get("SHOP_YOUTUBE", "@congkhangbike")

ENABLE_VISION    = True
ENABLE_MEMORY    = True
ENABLE_DUPLICATE = True
ENABLE_SCORE     = False
ENABLE_WHISPER   = True

EXPORT_SPECS = {
    "tiktok":    {"width": 1080, "height": 1920, "fps": 30, "bitrate": "8M"},
    "facebook":  {"width": 1080, "height": 1920, "fps": 30, "bitrate": "6M"},
    "youtube":   {"width": 1080, "height": 1920, "fps": 30, "bitrate": "8M"},
    "instagram": {"width": 1080, "height": 1350, "fps": 30, "bitrate": "6M"},
}
