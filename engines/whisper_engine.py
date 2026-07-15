"""
Module 4: Whisper Engine — Subtitle tự động từ giọng nói
Transcribe video tiếng Việt → tạo file SRT → burn vào video
"""
import os
import re
from pathlib import Path
from datetime import timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import WHISPER_MODEL, WHISPER_LANG, TEMP_DIR

# Whisper là optional — import khi cần
_whisper_model = None
_whisper_available = None


def _check_whisper() -> bool:
    global _whisper_available
    if _whisper_available is not None:
        return _whisper_available
    try:
        import whisper
        _whisper_available = True
    except ImportError:
        _whisper_available = False
    return _whisper_available


def _load_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    import whisper
    _whisper_model = whisper.load_model(WHISPER_MODEL)
    return _whisper_model


def _seconds_to_srt_time(seconds: float) -> str:
    """Chuyển giây → định dạng SRT timestamp: HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    ms = int((seconds - int(seconds)) * 1000)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_video(video_path: str, progress_cb=None) -> list[dict]:
    """
    Transcribe video tiếng Việt bằng Whisper.
    Trả về list segments: [{start, end, text}, ...]
    """
    if not _check_whisper():
        if progress_cb:
            progress_cb("⚠️ Whisper chưa cài. Chạy: pip install openai-whisper torch")
        return []

    try:
        if progress_cb:
            progress_cb("Đang load model Whisper...")
        model = _load_model()

        if progress_cb:
            progress_cb("Đang transcribe audio... (có thể mất 1-3 phút)")

        result = model.transcribe(
            video_path,
            language=WHISPER_LANG,
            task="transcribe",
            fp16=False,  # Dùng fp32 để tương thích CPU
            word_timestamps=False,
            verbose=False
        )

        segments = []
        for seg in result.get("segments", []):
            text = seg.get("text", "").strip()
            if text:
                segments.append({
                    "start": seg["start"],
                    "end":   seg["end"],
                    "text":  text
                })

        if progress_cb:
            progress_cb(f"Transcribe xong: {len(segments)} đoạn")

        return segments

    except Exception as e:
        if progress_cb:
            progress_cb(f"Lỗi Whisper: {str(e)}")
        return []


def segments_to_srt(segments: list[dict]) -> str:
    """Chuyển list segments thành nội dung file SRT"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_srt_time(seg["start"])
        end   = _seconds_to_srt_time(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")  # Dòng trắng phân cách
    return "\n".join(lines)


def save_srt(segments: list[dict], output_path: str) -> str | None:
    """Lưu file SRT từ segments. Trả về đường dẫn file."""
    if not segments:
        return None
    try:
        content = segments_to_srt(segments)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content, encoding="utf-8")
        return output_path
    except Exception:
        return None


def transcribe_and_save(video_path: str, output_dir: str = "", progress_cb=None) -> str | None:
    """
    All-in-one: transcribe video → lưu file SRT.
    Trả về đường dẫn file SRT hoặc None nếu thất bại.
    """
    segments = transcribe_video(video_path, progress_cb)
    if not segments:
        return None

    out_dir = output_dir or TEMP_DIR
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    stem = Path(video_path).stem
    srt_path = str(Path(out_dir) / f"{stem}.srt")
    return save_srt(segments, srt_path)


def is_available() -> bool:
    return _check_whisper()
