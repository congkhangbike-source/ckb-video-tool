import os
import sys
from pathlib import Path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import config
from engines.ai_engine import get_ai_engine, reload_engine

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="CKB Video Tool")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/status")
def api_status():
    ai = get_ai_engine()
    return {"api": ai.is_ready(), "model": config.CLAUDE_MODEL, "ffmpeg": False, "test_mode": "v5_ai_engine"}

@app.get("/")
def root():
    return {"status": "OK", "test_mode": "v5_ai_engine"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
