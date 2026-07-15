"""
Whisper Engine - dung faster-whisper (nhe hon openai-whisper 4-5 lan)
Transcribe video/audio tieng Viet -> list segments -> SRT file
Cai: pip install faster-whisper
"""
import os
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import WHISPER_MODEL, WHISPER_LANG, TEMP_DIR

_model = None
_available = None


def _check() -> bool:
    global _available
    if _available is not None:
        return _available
    try:
        from faster_whisper import WhisperModel
        _available = True
    except ImportError:
        _available = False
    return _available


def _load_model():
    global _model
    if _model is not None:
        return _model
    from faster_whisper import WhisperModel
    _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def _fmt_time(seconds: float) -> str:
    total = int(seconds)
    ms = int((seconds - total) * 1000)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_video(video_path: str, progress_cb=None) -> list:
    if not _check():
        if progress_cb:
            progress_cb(0, "Chua cai faster-whisper. Chay: pip install faster-whisper")
        return []
    try:
        if progress_cb:
            progress_cb(5, "Dang tai mo hinh Whisper...")
        model = _load_model()
        if progress_cb:
            progress_cb(20, "Dang doc giong noi...")
        segments_gen, info = model.transcribe(
            video_path,
            language=WHISPER_LANG,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        result = []
        for i, seg in enumerate(segments_gen):
            if seg.text.strip():
                result.append({
                    "start": seg.start,
                    "end":   seg.end,
                    "text":  seg.text.strip()
                })
            if progress_cb and i % 5 == 0:
                progress_cb(50 + min(i, 40), f"Dang doc... [{len(result)} doan]")
        if progress_cb:
            progress_cb(95, f"Hoan thanh: {len(result)} doan")
        return result
    except Exception as e:
        if progress_cb:
            progress_cb(0, f"Loi Whisper: {str(e)}")
        return []


def segments_to_srt(segments: list) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_fmt_time(seg['start'])} --> {_fmt_time(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def save_srt(segments: list, output_path: str) -> str:
    if not segments:
        return ""
    content = segments_to_srt(segments)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path


def transcribe_and_save(video_path: str, output_dir: str = "", progress_cb=None) -> str:
    segments = transcribe_video(video_path, progress_cb)
    if not segments:
        return ""
    out_dir = Path(output_dir) if output_dir else Path(TEMP_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    srt_path = str(out_dir / (Path(video_path).stem + ".srt"))
    return save_srt(segments, srt_path)


def is_available() -> bool:
    return _check()
