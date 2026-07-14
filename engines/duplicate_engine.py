"""
Module 16: Duplicate Engine — Phát hiện nội dung trùng lặp
So sánh script/caption mới với database để cảnh báo
"""
import difflib
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from config import DUPLICATE_THRESHOLD
except ImportError:
    DUPLICATE_THRESHOLD = 70
from engines.memory_engine import get_all_content


def _similarity(text1: str, text2: str) -> float:
    """Tính % giống nhau giữa 2 đoạn text (0-100)"""
    if not text1 or not text2:
        return 0.0
    ratio = difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    return round(ratio * 100, 1)


def check_duplicate(new_script: str, new_caption: str = "") -> dict:
    """
    Kiểm tra xem nội dung mới có trùng với content cũ không.
    Trả về dict kẽt quả.
    """
    if not new_script and not new_caption:
        return {"is_duplicate": False, "similarity": 0, "checked": False}

    existing = get_all_content(limit=200)
    if not existing:
        return {"is_duplicate": False, "similarity": 0, "checked": True, "message": "Chưa có content cũ để so sánh"}

    max_sim = 0.0
    most_similar = None

    for item in existing:
        old_script  = item.get("script", "") or ""
        old_caption = item.get("caption_tiktok", "") or ""

        # So sánh script
        sim_script = _similarity(new_script, old_script) if new_script and old_script else 0
        # So sánh caption TikTok
        sim_caption = _similarity(new_caption, old_caption) if new_caption and old_caption else 0

        # Lấy similarity cao nhất
        sim = max(sim_script, sim_caption)

        if sim > max_sim:
            max_sim = sim
            most_similar = item

    is_dup = max_sim >= DUPLICATE_THRESHOLD

    result = {
        "is_duplicate": is_dup,
        "similarity": max_sim,
        "checked": True,
    }

    if is_dup and most_similar:
        date_str = most_similar.get("ngay_tao", "")[:10]
        xe = most_similar.get("ten_xe", "")
        loai = most_similar.get("loai_video", "")
        result["similar_to"] = f"Video {xe} — {loai} ({date_str})"
        result["suggestions"] = _generate_suggestions(max_sim)
    elif max_sim >= 50:
        result["warning"] = f"Content khá giống ({max_sim:.0f}%) với content cũ — có thể thêm điểm khác biệt"
        result["suggestions"] = ["Thêm thông tin khuyến mã9 hoặc điểm nổi bật mới"]
    else:
        result["message"] = f"Content mới ({max_sim:.0f}% giống content cũ nhất) — Tốt!"

    return result


def _generate_suggestions(similarity: float) -> list[str]:
    return ["Thay hook", "Thay goc nhin", "Them thong tin moi"]
