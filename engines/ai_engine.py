"""AI Engine - Claude API wrapper for CKB Video Tool Railway"""
import os
import sys
import json
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import anthropic
    _ANTHROPIC_OK = True
except ImportError:
    _ANTHROPIC_OK = False

import config as _config
from config import (
    CLAUDE_API_KEY,
    DATABASE_DIR,
    PROMPTS_DIR,
    SHOP_NAME,
    SHOP_ADDRESS,
    SHOP_HOTLINE,
)


class AIEngine:
    def __init__(self, api_key=""):
        self.client = None
        key = api_key or CLAUDE_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
        if key and _ANTHROPIC_OK:
            try:
                self.client = anthropic.Anthropic(api_key=key)
            except Exception:
                pass

    def is_ready(self):
        return self.client is not None

    def reload(self, api_key=""):
        if not api_key or not _ANTHROPIC_OK:
            return False
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            return True
        except Exception:
            return False

    def generate(self, prompt, system="", max_tokens=2048):
        if not self.is_ready():
            return ""
        try:
            msg = self.client.messages.create(
                model=_config.CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system or f"Ban la tro ly cua {SHOP_NAME}.",
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text.strip()
        except Exception:
            return ""

    def vision(self, prompt, image_b64, media_type="image/jpeg"):
        if not self.is_ready() or not _ANTHROPIC_OK:
            return ""
        try:
            msg = self.client.messages.create(
                model=_config.CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": prompt}
                ]}]
            )
            return msg.content[0].text.strip()
        except Exception:
            return ""

    def chat(self, messages, system=""):
        if not self.is_ready():
            return "Chua co API key"
        try:
            msg = self.client.messages.create(
                model=_config.CLAUDE_MODEL,
                max_tokens=2048,
                system=[{"type": "text", "text": system or f"Ban la tro ly cua {SHOP_NAME}."}],
                messages=messages
            )
            return msg.content[0].text.strip()
        except Exception as e:
            return f"Loi: {str(e)}"


_ai_engine = None


def get_ai_engine():
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIEngine(CLAUDE_API_KEY or "")
    return _ai_engine


def reload_engine():
    global _ai_engine
    _ai_engine = None
