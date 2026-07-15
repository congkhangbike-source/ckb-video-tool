"""
CKB Video Tool - FastAPI Web Server
"""
import os, sys, json, uuid, asyncio, concurrent.futures
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

import config
from engines.ai_engine import get_ai_engine, reload_engine

app = FastAPI(title="CKB Video Tool")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
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
    vehicles = ["V1 Plus Lihaze", "DK S3", "DK EZ3", "Dibao Rosa", "V1 Plus Livo",
                "DK V2", "DK S5", "Weezee Plus 3", "Gogo Yaka", "Sky", "Lavia SX"]
    colors = ["Trang", "Den", "Hong", "Xanh", "Do", "Vang", "Bac", "Xam", "Tim", "Cam"]
    types = ["Review xe moi", "Ban giao xe", "Bao gia", "Khuyen mai", "So sanh xe",
             "Xe hoc sinh", "Kach hang danh gia", "Huong dan su dung"]
    audiences = ["Hoc sinh, sinh vien", "Phu nu noi tro", "Phu huynh mua cho con",
                 "Cong nhan, van phong", "Nguoi ve huu", "Tat ca doi tuong"]
    return {"vehicles": vehicles, "colors": colors, "types": types, "audiences": audiences}


@app.get("/api/voice_style/all")
def vs_all():
    try:
        from engines.voice_style_engine import load_style_profile
        result = []
        for slot in VALID_SLOTS:
            p = load_style_profile(slot)
            result.append({"slot": slot, "display_name": p.get("display_name", slot),
                           "sample_count": len(p.get("samples", [])), "analyzed": p.get("analyzed", False)})
        return {"profiles": result}
    except Exception as e:
        return {"profiles": [], "error": str(e)}


@app.get("/api/voice_style/{slot}")
def vs_get(slot: str):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile
        return load_style_profile(slot)
    except Exception as e:
        return {"slot": slot, "samples": [], "analyzed": False}


@app.post("/api/voice_style/{slot}/rename")
async def vs_rename(slot: str, req: dict = None):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile, save_style_profile
        p = load_style_profile(slot)
        name = (req or {}).get("name", slot)
        p["display_name"] = name
        save_style_profile(p, slot)
        return {"ok": True, "display_name": name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/add_sample")
async def vs_add_sample(slot: str, file: UploadFile = File(...)):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import add_sample
        tmp = BASE_DIR / "temp" / f"vs_{slot}_{uuid.uuid4().hex[:8]}{Path(file.filename or 'a.mp3').suffix}"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_bytes(await file.read())
        ok, msg, text = add_sample(slot, str(tmp))
        return {"ok": ok, "message": msg, "transcription": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/api/voice_style/{slot}/sample/{idx}")
def vs_remove_sample(slot: str, idx: int):
    try:
        from engines.voice_style_engine import remove_sample
        ok, msg = remove_sample(slot, idx)
        return {"ok": ok, "message": msg}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/analyze")
def vs_analyze(slot: str):
    try:
        from engines.voice_style_engine import analyze_style
        ok, msg = analyze_style(slot)
        return {"ok": ok, "message": msg}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/clear")
def vs_clear(slot: str):
    try:
        from engines.voice_style_engine import load_style_profile, save_style_profile, _default_profile
        save_style_profile(_default_profile(slot), slot)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/voice_style/{slot}/add_from_file")
async def vs_add_from_file(slot: str, file: UploadFile = File(...)):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import add_sample_from_video
        tmp = BASE_DIR / "temp" / f"vs_{slot}_{uuid.uuid4().hex[:8]}{Path(file.filename or 'v.mp4').suffix}"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_bytes(await file.read())
        ok, msg, text = add_sample_from_video(slot, str(tmp))
        return {"ok": ok, "message": msg, "transcription": text}
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
