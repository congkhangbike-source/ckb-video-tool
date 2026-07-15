import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="CKB Video Tool")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/status")
def api_status():
    return {"api": False, "model": "claude-sonnet-5", "ffmpeg": False, "test_mode": "v3_baseline"}

@app.get("/api/voice_style/{slot}")
def vs_get(slot: str):
    return {"slot": slot, "samples": [], "analyzed": False, "test_mode": True}

@app.get("/api/voice_style/all")
def vs_all():
    return {"profiles": [], "test_mode": True}

@app.get("/")
def root():
    return {"status": "Railway OK", "test_mode": "v3_baseline"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
