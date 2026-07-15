"""
Module: Voice Style Engine — Học giọng điệu nhiều người
Hỗ trợ tối đa 3 profile giọng điệu song song (person_1, person_2, person_3).
Mỗi profile có bộ mẫu + pattern riêng, inject vào AI khi sinh content.
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_DIR

# Mỗi slot lưu thành 1 file riêng
VALID_SLOTS = ("person_1", "person_2", "person_3")

def _style_file(slot: str) -> Path:
    slot = slot if slot in VALID_SLOTS else "person_1"
    return Path(DATABASE_DIR) / f"voice_style_{slot}.json"


# ─── Đọc / ghi profile ────────────────────────────────────────────────────────

def load_style_profile(slot: str = "person_1") -> dict:
    f = _style_file(slot)
    if not f.exists():
        return _default_profile(slot)
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        default = _default_profile(slot)
        for k, v in default.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return _default_profile(slot)


def save_style_profile(profile: dict, slot: str = "person_1") -> bool:
    try:
        f = _style_file(slot)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def _default_profile(slot: str = "person_1") -> dict:
    default_names = {"person_1": "Người 1", "person_2": "Người 2", "person_3": "Người 3"}
    return {
        "slot": slot,
        "display_name": default_names.get(slot, "Người 1"),
        "samples": [],
        "analyzed": False,
        "pattern": {
            "avg_sentence_len": 0,
            "uses_emoji": False,
            "emoji_freq": "low",
            "preferred_cta": "",
            "common_phrases": [],
            "tone": "neutral",
            "address_style": "minh/ban",
        },
        "style_prompt": "",
        "updated_at": "",
    }


# ─── Thêm / xoá mẫu ──────────────────────────────────────────────────────────

def add_sample(text: str, label: str = "", slot: str = "person_1") -> tuple[bool, str]:
    text = text.strip()
    if not text or len(text) < 20:
        return False, "Mẫu quá ngắn — tối thiểu 20 ký tự"
    profile = load_style_profile(slot)
    if text in [s["text"] for s in profile["samples"]]:
        return False, "Mẫu này đã có rồi"
    profile["samples"].append({
        "text":  text,
        "label": label or f"Mẫu {len(profile['samples']) + 1}",
        "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    profile["analyzed"] = False
    save_style_profile(profile, slot)
    return True, f"Đã thêm mẫu #{len(profile['samples'])} vào {profile['display_name']}"


def remove_sample(index: int, slot: str = "person_1") -> tuple[bool, str]:
    profile = load_style_profile(slot)
    if index < 0 or index >= len(profile["samples"]):
        return False, "Index không hợp lệ"
    removed = profile["samples"].pop(index)
    profile["analyzed"] = False
    save_style_profile(profile, slot)
    return True, f"Đã xoá mẫu: {removed['label']}"


# ─── Học từ video ─────────────────────────────────────────────────────────────

def add_sample_from_video(video_path: str, label: str = "", slot: str = "person_1") -> tuple[bool, str, str]:
    """
    Dùng Whisper transcribe video → thêm transcript làm mẫu giọng điệu.
    Trả về (success, message, transcript_text)
    """
    try:
        from engines.whisper_engine import transcribe_video, is_available as whisper_ok
    except ImportError:
        return False, "Whisper chưa cài. Chạy: pip install openai-whisper torch", ""

    if not whisper_ok():
        return False, "Whisper chưa cài. Chạy: pip install openai-whisper torch", ""

    if not Path(video_path).exists():
        return False, f"Không tìm thấy file: {video_path}", ""

    segments = transcribe_video(video_path)
    if not segments:
        return False, "Không trích được lời nói — kiểm tra âm thanh trong video", ""

    full_text = " ".join(seg["text"].strip() for seg in segments if seg.get("text", "").strip())
    full_text = full_text.strip()

    if len(full_text) < 20:
        return False, f"Transcript quá ngắn ({len(full_text)} ký tự)", full_text

    auto_label = label or Path(video_path).stem[:40]
    ok, msg = add_sample(full_text, auto_label, slot)

    preview = full_text[:200] + ("..." if len(full_text) > 200 else "")
    if ok:
        profile = load_style_profile(slot)
        return True, f"{msg}\n📝 Transcript ({len(full_text)} ký tự):\n{preview}", full_text
    return False, msg, full_text


# ─── Phân tích pattern ────────────────────────────────────────────────────────

def analyze_style(slot: str = "person_1", ai_engine=None) -> dict:
    """Phân tích pattern từ các mẫu — rule-based hoặc AI nếu có key."""
    profile = load_style_profile(slot)
    samples = profile.get("samples", [])

    if not samples:
        return {"error": f"Profile '{profile['display_name']}' chưa có mẫu nào"}

    all_text = "\n\n---\n\n".join(s["text"] for s in samples)

    # ── Rule-based ────────────────────────────────────────────────
    sentences = []
    for s in samples:
        parts = re.split(r'[.!?]', s["text"])
        sentences.extend([p.strip() for p in parts if p.strip()])

    avg_len = round(sum(len(s) for s in sentences) / max(len(sentences), 1))

    emoji_count = len(re.findall(r'[\U0001F300-\U0001FFFF]', all_text))
    uses_emoji  = emoji_count > 0
    emoji_freq  = "high" if emoji_count > 10 else ("medium" if emoji_count > 3 else "low")

    minh = all_text.lower().count("mình")
    toi  = all_text.lower().count("tôi")
    ban  = all_text.lower().count("bạn")
    anh  = all_text.lower().count("anh") + all_text.lower().count("chị")
    if minh >= toi:
        address_style = "mình/bạn" if ban >= anh else "mình/anh chị"
    else:
        address_style = "tôi/bạn"

    casual_words = ["thật ra", "thực tế", "mình thấy", "nói thật", "kể thật"]
    formal_words = ["chúng tôi", "trân trọng", "quý khách", "xin kính"]
    casual_score = sum(all_text.lower().count(w) for w in casual_words)
    formal_score = sum(all_text.lower().count(w) for w in formal_words)
    tone = "casual" if casual_score > formal_score else ("formal" if formal_score > 0 else "neutral")

    phrase_candidates = [
        "thật ra", "thực tế mà nói", "mình thấy", "thành thật mà nói",
        "nói thật", "đi ngon", "chiếc xe", "xe này", "inbox",
        "ghé cửa hàng", "comment", "báo giá", "tư vấn miễn phí",
    ]
    common_phrases = [ph for ph in phrase_candidates if all_text.lower().count(ph) >= 2]

    cta_scores = {
        "comment": all_text.lower().count("comment"),
        "inbox":   all_text.lower().count("inbox"),
        "ghe":     all_text.lower().count("ghé"),
    }
    preferred_cta = max(cta_scores, key=cta_scores.get)

    rule_pattern = {
        "avg_sentence_len": avg_len,
        "uses_emoji":       uses_emoji,
        "emoji_freq":       emoji_freq,
        "preferred_cta":    preferred_cta,
        "common_phrases":   common_phrases[:6],
        "tone":             tone,
        "address_style":    address_style,
    }

    # ── AI phân tích sâu ────────────────────────────────────────
    style_prompt = ""
    display_name = profile.get("display_name", slot)
    if ai_engine and ai_engine.is_ready() and len(samples) >= 2:
        try:
            ai_prompt = f"""Phân tích phong cách viết content của "{display_name}" — người bán xe điện tại Hải Phòng.
Dưới đây là {len(samples)} mẫu script/caption họ đã TỰ viết:

{all_text}

Viết 1 đoạn instruction ngắn (100-150 từ) để AI khác bắt chước ĐÚNG giọng điệu, cách dùng từ,
nhịp câu, emoji, và phong cách CTA của "{display_name}".
Bắt đầu bằng: "Viết theo phong cách của {display_name}..."
Chỉ trả về đoạn instruction, không giải thích thêm."""

            msg = ai_engine.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": ai_prompt}]
            )
            style_prompt = msg.content[0].text.strip()
        except Exception:
            pass

    if not style_prompt:
        emoji_note = (
            f"Dùng emoji {'nhiều' if emoji_freq=='high' else 'vừa phải' if emoji_freq=='medium' else 'ít'}."
            if uses_emoji else "Không dùng emoji."
        )
        cta_note = {
            "comment": "CTA hay dùng: 'Comment báo giá — mình nhắn lại ngay'.",
            "inbox":   "CTA hay dùng: 'Inbox Zalo để hỏi giá — tư vấn miễn phí'.",
            "ghe":     "CTA hay dùng: 'Ghé cửa hàng xem trực tiếp'.",
        }.get(preferred_cta, "")
        phrases_note = f"Hay dùng: {', '.join(common_phrases[:4])}." if common_phrases else ""
        style_prompt = (
            f"Viết theo phong cách của {display_name}: {tone}, {address_style}. "
            f"Câu ngắn ~{avg_len} ký tự. {emoji_note} {phrases_note} {cta_note}"
        ).strip()

    profile["pattern"]     = rule_pattern
    profile["style_prompt"] = style_prompt
    profile["analyzed"]    = True
    profile["updated_at"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_style_profile(profile, slot)

    return {
        "pattern":      rule_pattern,
        "style_prompt": style_prompt,
        "sample_count": len(samples),
        "display_name": display_name,
    }


# ─── Lấy style injection cho AI ──────────────────────────────────────────────

def get_style_injection(slot: str = "person_1") -> str:
    """Trả về style_prompt để inject vào system prompt. Rỗng nếu chưa có."""
    if not slot or slot == "Không dùng giọng điệu (mặc định AI)":
        return ""
    # Map tên hiển thị → slot ID
    slot_id = _resolve_slot(slot)
    profile = load_style_profile(slot_id)
    if not profile.get("samples"):
        return ""
    if not profile.get("analyzed"):
        analyze_style(slot_id)
        profile = load_style_profile(slot_id)
    return profile.get("style_prompt", "")


def _resolve_slot(slot_or_name: str) -> str:
    """Chấp nhận cả 'person_1' lẫn 'Người 1' lẫn tên tuỳ chỉnh."""
    if slot_or_name in VALID_SLOTS:
        return slot_or_name
    mapping = {"Người 1": "person_1", "Người 2": "person_2", "Người 3": "person_3"}
    if slot_or_name in mapping:
        return mapping[slot_or_name]
    # Tìm theo display_name
    for s in VALID_SLOTS:
        p = load_style_profile(s)
        if p.get("display_name") == slot_or_name:
            return s
    return "person_1"


# ─── Tiện ích UI ──────────────────────────────────────────────────────────────

def get_sample_count(slot: str = "person_1") -> int:
    return len(load_style_profile(slot).get("samples", []))


def format_profile_summary(slot: str = "person_1") -> str:
    profile = load_style_profile(slot)
    samples = profile.get("samples", [])
    name = profile.get("display_name", slot)

    if not samples:
        return f"👤 {name}\nChưa có mẫu nào. Thêm ít nhất 3 mẫu (upload video hoặc dán script)."

    lines = [f"👤 {name} — {len(samples)} mẫu giọng điệu"]
    if profile.get("analyzed"):
        p = profile.get("pattern", {})
        lines.append(f"🗣  Phong cách: {p.get('tone','?')} — {p.get('address_style','?')}")
        lines.append(f"📝 Câu trung bình: ~{p.get('avg_sentence_len','?')} ký tự")
        if p.get("uses_emoji"):
            lines.append(f"😀 Emoji: {p.get('emoji_freq','?')}")
        if p.get("common_phrases"):
            lines.append(f"💬 Hay dùng: {', '.join(p['common_phrases'][:3])}")
        lines.append(f"\n✅ Style prompt đã sẵn sàng — AI sẽ viết giống {name}")
        sp = profile.get("style_prompt", "")
        if sp:
            lines.append(f"\n📌 Style prompt:\n{sp[:300]}{'...' if len(sp)>300 else ''}")
    else:
        lines.append("⚠️  Chưa phân tích — nhấn 'Phân tích giọng điệu' để kích hoạt")

    lines.append("\nDanh sách mẫu:")
    for i, s in enumerate(samples):
        preview = s["text"][:70].replace("\n", " ")
        lines.append(f"  [{i+1}] {s['label']}: {preview}...")
    return "\n".join(lines)


def get_all_profiles_summary() -> str:
    """Tóm tắt cả 3 profile để hiển thị tổng quan."""
    parts = []
    for slot in VALID_SLOTS:
        p = load_style_profile(slot)
        name = p.get("display_name", slot)
        count = len(p.get("samples", []))
        analyzed = "✅" if p.get("analyzed") else "⚠️"
        parts.append(f"{analyzed} {name}: {count} mẫu")
    return " | ".join(parts)
