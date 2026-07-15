"""CKB Video Tool - FastAPI Backend"""
import os
import sys
import uuid
import concurrent.futures
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import config
from engines.ai_engine import get_ai_engine, reload_engine

app = FastAPI(title="CKB Video Tool")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
VALID_SLOTS = ("person_1", "person_2", "person_3")


@app.get("/api/status")
def api_status():
    ai = get_ai_engine()
    ffmpeg_ok = False
    try:
        from engines.video_engine import is_ffmpeg_available
        ffmpeg_ok = is_ffmpeg_available()
    except Exception:
        pass
    return {"api": ai.is_ready(), "model": config.CLAUDE_MODEL, "ffmpeg": ffmpeg_ok}


@app.get("/api/data")
def api_data():
    return {
        "vehicles": [
            "V1 Plus Lihaze", "V1 Plus Livo", "DK S3", "DK EZ3", "DK V2", "DK S5",
            "Dibao Rosa", "Weezee Plus 3", "Gogo Yaka", "Sky", "Lavia SX", "Lavia Plus",
            "V1 Sonco", "Kren", "G9 S New", "JVC G9 NFC", "Sonco Bun", "V1 Dior JVC"
        ],
        "colors": [
            "Den", "Trang", "Do", "Cam", "Vang", "Xanh la", "Xanh duong", "Xanh navy",
            "Tim", "Hong", "Bac", "Xam", "Nau", "Kem", "Xanh ngoc", "Hong phan", "Vang dong", "Den bong"
        ],
        "types": [
            "Review xe moi", "So sanh xe", "Demo tinh nang", "Unboxing",
            "Khach hang danh gia", "Huong dan su dung", "Khuyen mai uu dai",
            "Behind the scenes", "Ky thuat sua chua", "Story thuong hieu"
        ],
        "audiences": [
            "Hoc sinh sinh vien", "Phu huynh mua cho con", "Nhan vien van phong",
            "Noi tro gia dinh", "Nguoi lon tuoi", "Khach mua xe cu", "Khach can sua chua"
        ]
    }


@app.get("/api/voice_style/all")
def vs_all():
    try:
        from engines.voice_style_engine import load_style_profile
        result = []
        for slot in VALID_SLOTS:
            p = load_style_profile(slot)
            result.append({
                "slot": slot,
                "display_name": p.get("display_name", slot),
                "sample_count": len(p.get("samples", [])),
                "analyzed": p.get("analyzed", False)
            })
        return {"profiles": result}
    except Exception as e:
        return {"profiles": [], "error": str(e)}


@app.get("/api/voice_style/{slot}")
def vs_get(slot: str):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile
        return load_style_profile(slot)
    except Exception as e:
        return {"slot": slot, "samples": [], "analyzed": False}


@app.post("/api/voice_style/{slot}/rename")
async def vs_rename(slot: str, body: dict = Body(default={})):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile, save_style_profile
        p = load_style_profile(slot)
        # Frontend gá»­i {display_name: "..."} 
        name = body.get("display_name") or body.get("name") or slot
        p["display_name"] = name
        save_style_profile(p, slot)
        return {"ok": True, "display_name": p["display_name"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/add_sample")
async def vs_add_sample(slot: str, file: UploadFile = File(...), label: str = Query(default="")):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot")
    try:
        from engines.voice_style_engine import add_sample
        suffix = Path(file.filename or "a.mp3").suffix or ".mp3"
        tmp = BASE_DIR / "temp" / f"vs_{slot}_{uuid.uuid4().hex[:8]}{suffix}"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_bytes(await file.read())
        ok, msg, text = add_sample(slot, str(tmp))
        return {"ok": ok, "message": msg, "transcription": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/add_from_file")
async def vs_add_from_file(slot: str, file: UploadFile = File(...), label: str = Query(default="")):
    """Upload file video/MP3 - frontend calls this endpoint"""
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot")
    try:
        suffix = Path(file.filename or "upload").suffix or ".mp4"
        tmp = BASE_DIR / "temp" / f"vs_{slot}_{uuid.uuid4().hex[:8]}{suffix}"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_bytes(await file.read())
        # Try video extraction first, fallback to audio sample
        ok, msg, text = False, "", ""
        try:
            from engines.voice_style_engine import add_sample_from_video
            ok, msg, text = add_sample_from_video(str(tmp), label=label, slot=slot)
        except Exception as e_vs:
            ok, msg, text = False, f"Loi xu ly video: {str(e_vs)}", ""
        return {"ok": ok, "message": msg, "transcription": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/api/voice_style/{slot}/sample/{idx}")
def vs_remove_sample(slot: str, idx: int):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot")
    try:
        from engines.voice_style_engine import remove_sample
        ok, msg = remove_sample(slot, idx)
        return {"ok": ok, "message": msg}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/analyze")
def vs_analyze(slot: str):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot")
    try:
        from engines.voice_style_engine import analyze_style
        ok, msg = analyze_style(slot)
        return {"ok": ok, "message": msg}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/clear")
def vs_clear(slot: str):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile, save_style_profile
        p = load_style_profile(slot)
        p["samples"] = []
        p["analyzed"] = False
        save_style_profile(p, slot)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/")
def frontend():
    p = BASE_DIR / "pages" / "index.html"
    if p.exists():
        return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CKB Video Tool</h1>")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
