"""
AI Engine - Claude API integration for CKB Video Tool
"""
import json
import os
import base64
from pathlib import Path

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config as _config
from config import (
    CLAUDE_API_KEY,
    DATABASE_DIR, PROMPTS_DIR,
    SHOP_NAME, SHOP_ADDRESS, SHOP_HOTLINE,
)


class AIEngine:
    def __init__(self, api_key: str = ""):
        self.client = None
        key = api_key or CLAUDE_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
        if key and ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic(api_key=key)
            except Exception:
                pass

    def is_ready(self) -> bool:
        return self.client is not None

    def reload(self, api_key: str):
        if not ANTHROPIC_AVAILABLE:
            return False
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                return True
            except Exception:
                return False
        return False

    def _load_vehicle(self, ten_xe: str) -> dict:
        try:
            p = Path(DATABASE_DIR) / "vehicles.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            for xe in data.get("xe_dien", []):
                if xe["ten"].lower() == ten_xe.lower():
                    return {"xe": xe, "qua_tang": data.get("qua_tang_kem", []), "mau_sac": data.get("mau_sac", [])}
            return {"xe": {"ten": ten_xe, "gia": None, "bao_hanh": "12 thang"}, "qua_tang": [], "mau_sac": []}
        except Exception:
            return {"xe": {"ten": ten_xe}, "qua_tang": [], "mau_sac": []}

    def _load_promotion(self) -> str:
        try:
            p = Path(DATABASE_DIR) / "promotion.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            kms = data.get("khuyen_mai", [])
            return json.dumps(kms, ensure_ascii=False) if kms else "Khong co khuyen mai"
        except Exception:
            return "Khong co khuyen mai"

    def generate_content(self, ten_xe, mau_xe, loai_video, doi_tuong, diem_noi_bat="", thoi_luong="30 giay", voice_slot="", platforms=None, progress_cb=None, model="", voice_style="") -> dict:
        if not self.is_ready():
            return {"error": "Chua co API key. Vao Tab Cai dat de nhap Claude API key."}

        vd = self._load_vehicle(ten_xe)
        xe = vd["xe"]
        gia_str = f"{xe['gia']:,.0f}d".replace(",", ".") if xe.get("gia") else "Lien he cua hang"
        qua = ", ".join(vd["qua_tang"]) or "Theo chinh sach cua hang"
        promotion = self._load_promotion()

        plats = set(platforms) if platforms else {"TikTok", "Facebook"}
        cap_fields = ""
        if "TikTok" in plats:
            cap_fields += '"caption_tiktok": "Caption TikTok ngan gon",
'
        if "Facebook" in plats:
            cap_fields += '"caption_facebook": "Caption Facebook day du",
'

        prompt = (
            f"Ban la chuyen gia content TikTok cho {SHOP_NAME}.\n"
            f"Tham so video: xe={ten_xe}, mau={mau_xe}, loai={loai_video}, doi tuong={doi_tuong}, thoi luong={thoi_luong}\n"
            f"Gia: {gia_str}, qua tang: {qua}, khuyen mai: {promotion}\n\n"
            f"Tra ve JSON (khong markdown):\n"
            + '{' + "\n"
            + f'"script": "Script {thoi_luong} toi da",\n'
            + '"hook_text": "Hook 5-7 tu",\n'
            + '"cta_text": "CTA 1 hanh dong",\n'
            + cap_fields
            + '"hashtag": "#xedien #xedienhp"\n'
            + '}'
        )

        try:
            if progress_cb:
                progress_cb("Dang goi Claude API")
            msg = self.client.messages.create(
                model=(model or _config.CLAUDE_MODEL),
                max_tokens=4096,
                system=[{"type": "text", "text": f"Ban la AI tro ly cua {SHOP_NAME}. Tra ve JSON hop le."}],
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "Loi parse JSON"}
        except Exception as e:
            return {"error": str(e)}

    def analyze_images(self, image_paths: list, prompt: str) -> str:
        if not self.is_ready():
            return ""
        try:
            content = []
            for img_path in image_paths[:8]:
                try:
                    with open(img_path, "rb") as f:
                        img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
                    content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}})
                except Exception:
                    pass
            if not content:
                return ""
            msg = self.client.messages.create(
                model=_config.CLAUDE_MODEL, max_tokens=1024,
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}] + content}],
            )
            return msg.content[0].text.strip()
        except Exception:
            return ""

    def chat(self, messages: list, system: str = "") -> str:
        """General chat completion"""
        if not self.is_ready():
            return "Chua co API key"
        try:
            sys_prompt = [{"type": "text", "text": system}] if system else [{"type": "text", "text": f"Ban la tro ly thong minh cua {SHOP_NAME}."}]
            msg = self.client.messages.create(
                model=_config.CLAUDE_MODEL, max_tokens=2048,
                system=sys_prompt,
                messages=messages,
            )
            return msg.content[0].text.strip()
        except Exception as e:
            return f"Loi: {str(e)}"


_ai_engine: AIEngine | None = None

def get_ai_engine() -> AIEngine:
    global _ai_engine
    if _ai_engine is None:
        from config import CLAUDE_API_KEY
        _ai_engine = AIEngine(CLAUDE_API_KEY or "")
    return _ai_engine

def reload_engine():
    global _ai_engine
    _ai_engine = None
