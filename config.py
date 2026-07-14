"""
CKB Video Tool — Cấu hình toàn bộ hệ thống
Chỉnh sửa file này để tùy chỉnh tool
"""
import os

# =============================================
# API KEYS
# =============================================
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL   = "claude-sonnet-5"

# =============================================
# FFMPEG
# =============================================
FFMPEG_PATH	 } os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE_PATH = os.environ.get("FFPROBE_PATH", "ffprobe")

# =============================================
# THƪ MỤC
# =============================================
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

# =============================================
# CÀI CQUOT VIDEO
# =============================================
VIDEO_WIDTH    = 1080
VIDEO_HEIGHT   = 1920
FONT_SIZE      = 38
LOGO_WIDTH     = 120
LOGO_HEIGHT    = 60
MUSIC_VOLUME = 0.3

# =============================================
# THÔNG TIN CỦA HÀNG
# =============================================
SHOP_NAME     = "Công Khang Bike"
SHOP_ADDRESS  = "496 Đông Hải, Hai An, Hải Phong"
SHOP_HOTLINE  = "0762030888"
SHOP_ZALO     = "0762030888"

# =============================================
# FEATURE FLAGS
# =============================================
ENABLE_VISION        = True
ENABLE_MEMORY        = True
ENABLE_DUPLICATE     = True
ENABLE_SCORE         = True

# =============================================
# EXPORT SPECS
# =============================================
EXPORT_SPEC = {
    "tiktok":    {"width": 1080, "height": 1920, "fps": 30, "bitrate": "8M"},
    "facebook":  {"width": 1080, "height": 1920, "fps": 30, "bitrate": "6M"},
    "youtube":   {"width": 1080, "height": 1920, "fps": 30, "bitrate": "8M"},
}
