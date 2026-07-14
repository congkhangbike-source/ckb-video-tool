"""
CKB Video Tool — FastAPI Web Server
Giao dien web chuyen nghiep thay the Gradio
"""
import os, sys, json, uuid, asyncio, concurrent.futures
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Thieu thu vien. Dang cai fastapi uvicorn...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "--quiet"])
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn

import config
from engines.ai_engine import get_ai_engine, reload_engine

app = FastAPI(title="CKB Video Tool")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


# Status
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


# App data
@app.get("/api/data")
def api_data():
    vehicles, colors = [], []
    try:
        p = BASE_DIR / "database" / "vehicles.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        vehicles = [x["ten"] for x in data.get("xe_dien", [])]
        colors = data.get("mau_sac", [])
    except Exception:
        vehicles = ["V1 Plus Lihaze", "DK S3", "DK EZ3", "Dibao Rosa"]
        colors = ["Trang", "Den", "Hong", "Xanh", "Do", "Vang", "Bac"]

    types = ["Review xe", "Ban giao xe", "Bao gia", "Khuyen mai",
             "So sanh xe", "Xe hoc sinh", "Xe nu", "Sua chua"]
    try:
        from engines.timeline_engine import get_all_types
        types = get_all_types()
    except Exception:
        pass

    audiences = [
        "Hoc sinh, sinh vien", "Phu nu noi tro", "Phu huynh mua cho con",
        "Cong nhan, van phong", "Nguoi ve huu", "Tat ca doi tuong"
    ]
    highlights = [
        "Pin lau, sac nhanh", "Tiet kiem dien", "Thiet ke dep, hien dai",
        "Gia tot nhat khu vuc", "Bao hanh chinh hang", "Co xe the thao",
        "Phu hop hoc sinh", "Tang kem phu kien", "Tra gop 0%"
    ]
    return {"vehicles": vehicles, "colors": colors, "types": types,
            "audiences": audiences, "highlights": highlights}


# Analyze video
@app.post("/api/analyze")
async def api_analyze(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename or "v.mp4").suffix or ".mp4"
    tmp = BASE_DIR / "temp" / f"up_{job_id}{ext}"
    tmp.parent.mkdir(exist_ok=True)
    content = await file.read()
    tmp.write_bytes(content)

    result = {
        "video_path": str(tmp), "job_id": job_id,
        "vision": "", "quality": "", "timeline": "",
        "xe_detect": "", "mau_detect": "", "loai_detect": "",
        "duration": 0, "size": f"{len(content)/1024/1024:.1f} MB",
    }
    try:
        from engines.video_engine import get_video_info
        info = get_video_info(str(tmp))
        result["duration"] = round(info.get("duration", 0), 1)
    except Exception:
        pass

    ai = get_ai_engine()
    if not ai.is_ready():
        result["error"] = "Chua co API key"
        return result

    loop = asyncio.get_event_loop()

    def _vision():
        try:
            from engines.vision_engine import analyze_video, format_vision_result
            return analyze_video(str(tmp), ai, frames=config.VISION_FRAMES)
        except Exception as e:
            return {"error": str(e)}

    def _quality():
        try:
            from engines.quality_engine import analyze_quality, format_quality_report
            return format_quality_report(analyze_quality(str(tmp)))
        except Exception as e:
            return f"Loi: {str(e)[:80]}"

    try:
        vision_raw = await loop.run_in_executor(_executor, _vision)
        if "error" not in vision_raw:
            from engines.vision_engine import format_vision_result
            result["vision"] = format_vision_result(vision_raw)
            result["xe_detect"]   = vision_raw.get("xe", "")
            result["mau_detect"]  = vision_raw.get("mau", "")
            result["loai_detect"] = vision_raw.get("loai", "")
        else:
            result["vision"] = f"Loi vision: {vision_raw['error'][:80]}"
    except Exception as e:
        result["vision"] = f"Loi vision: {str(e)[:60]}"

    try:
        result["quality"] = await loop.run_in_executor(_executor, _quality)
    except Exception:
        pass

    return result


# Generate content
class GenerateRequest(BaseModel):
    ten_xe: str
    mau_xe: str = ""
    loai_video: str = "Review xe"
    doi_tuong: str = "Hoc sinh, sinh vien"
    diem_noi_bat: str = ""
    thoi_luong: str = "30 giay"
    platforms: list = ["TikTok", "Facebook"]
    model: str = ""
    voice_slot: str = ""


@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    ai = get_ai_engine()
    if not ai.is_ready():
        raise HTTPException(400, "Chua co API key")
    loop = asyncio.get_event_loop()
    # Inject voice style nếu có
    voice_injection = ""
    if req.voice_slot:
        try:
            from engines.voice_style_engine import get_style_injection
            voice_injection = get_style_injection(req.voice_slot)
        except Exception:
            pass
    # Dùng model từ frontend nếu có
    active_model = req.model if req.model else config.CLAUDE_MODEL
    def _run():
        return ai.generate_content(
            ten_xe=req.ten_xe, mau_xe=req.mau_xe, loai_video=req.loai_video,
            doi_tuong=req.doi_tuong, diem_noi_bat=req.diem_noi_bat,
            thoi_luong=req.thoi_luong, platforms=req.platforms,
            model=active_model, voice_style=voice_injection,
        )
    try:
        return await loop.run_in_executor(_executor, _run)
    except Exception as e:
        raise HTTPException(500, str(e))


# History
@app.get("/api/history")
def api_history(limit: int = 20, search: str = ""):
    try:
        from engines.memory_engine import get_all_content, search_content
        items = search_content(search, None) if search else get_all_content(limit=limit)
        return {"items": items or [], "total": len(items or [])}
    except Exception as e:
        return {"items": [], "total": 0, "error": str(e)}


@app.get("/api/stats")
def api_stats():
    try:
        from engines.memory_engine import get_stats
        return get_stats()
    except Exception:
        return {"total": 0, "avg_viral_score": 0, "top_xe": [], "by_type": []}


# Model
class ModelReq(BaseModel):
    model: str

_MODEL_LABELS = {
    "claude-haiku-4-5-20251001": "Haiku",
    "claude-sonnet-5":           "Sonnet 5",
    "claude-opus-4-8":           "Opus 4.8",
}

@app.post("/api/model")
def api_change_model(req: ModelReq):
    if req.model not in _MODEL_LABELS:
        raise HTTPException(400, "Model khong hop le")
    config.CLAUDE_MODEL = req.model
    return {"ok": True, "model": req.model, "label": _MODEL_LABELS[req.model]}


# Custom Prompt
class CustomPromptReq(BaseModel):
    prompt: str
    ten_xe: str = ""
    mau_xe: str = ""
    video_context: str = ""

@app.post("/api/custom_generate")
async def api_custom_generate(req: CustomPromptReq):
    ai = get_ai_engine()
    if not ai.is_ready():
        raise HTTPException(400, "Chua co API key")
    loop = asyncio.get_event_loop()
    def _run():
        try:
            import anthropic as _ant
            client = _ant.Anthropic(api_key=config.CLAUDE_API_KEY)
            ctx = []
            if req.ten_xe:
                ctx.append(f"Xe dien: {req.ten_xe}")
            if req.mau_xe:
                ctx.append(f"Mau: {req.mau_xe}")
            if req.video_context and req.video_context.strip() not in ("", "-"):
                ctx.append(f"Phan tich video: {req.video_context[:400]}")
            shop = (f"Cua hang: {config.SHOP_NAME}\n"
                    f"Dia chi: {config.SHOP_ADDRESS}\n"
                    f"Hotline: {config.SHOP_HOTLINE}")
            full = ""
            if ctx:
                full += "Thong tin san pham:\n" + "\n".join(ctx) + "\n\n"
            full += f"Thong tin cua hang:\n{shop}\n\n"
            full += f"Yeu cau:\n{req.prompt}"
            msg = client.messages.create(
                model=config.CLAUDE_MODEL, max_tokens=2000,
                messages=[{"role": "user", "content": full}],
            )
            return {"result": msg.content[0].text}
        except Exception as e:
            return {"result": f"Loi: {str(e)}"}
    return await loop.run_in_executor(_executor, _run)


# Voiceover
class VoiceoverReq(BaseModel):
    text: str
    voice: str = "vi-VN-HoaiMyNeural"

@app.post("/api/voiceover")
async def api_voiceover(req: VoiceoverReq):
    try:
        import edge_tts
        out_name = f"voice_{uuid.uuid4().hex[:8]}.mp3"
        out_path = BASE_DIR / "output" / out_name
        out_path.parent.mkdir(exist_ok=True)
        communicate = edge_tts.Communicate(req.text, req.voice)
        await communicate.save(str(out_path))
        return {"ok": True, "url": f"/files/{out_name}", "filename": out_name}
    except ImportError:
        raise HTTPException(500, "edge-tts chua cai. Chay: pip install edge-tts")
    except Exception as e:
        raise HTTPException(500, f"Loi voiceover: {str(e)}")


# Subtitle (Whisper)
class SubtitleReq(BaseModel):
    video_path: str

def _fmt_srt(sec: float) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    ms = int((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

@app.post("/api/subtitle")
async def api_subtitle(req: SubtitleReq):
    loop = asyncio.get_event_loop()
    def _run():
        try:
            import whisper
            model = whisper.load_model(config.WHISPER_MODEL)
            result = model.transcribe(req.video_path, language=config.WHISPER_LANG)
            srt_name = f"sub_{uuid.uuid4().hex[:8]}.srt"
            srt_path = BASE_DIR / "captions" / srt_name
            srt_path.parent.mkdir(exist_ok=True)
            lines = []
            for i, seg in enumerate(result["segments"], 1):
                lines.append(f"{i}\n{_fmt_srt(seg['start'])} --> {_fmt_srt(seg['end'])}\n{seg['text'].strip()}\n")
            srt_path.write_text("\n".join(lines), encoding="utf-8")
            return {"ok": True, "url": f"/files/{srt_name}", "filename": srt_name,
                    "text": result.get("text", "")[:500]}
        except ImportError:
            return {"ok": False, "error": "Whisper chua cai. Chay: pip install openai-whisper"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return await loop.run_in_executor(_executor, _run)


# Thumbnail
class ThumbnailReq(BaseModel):
    video_path: str
    ten_xe: str = ""

@app.post("/api/thumbnail")
async def api_thumbnail(req: ThumbnailReq):
    loop = asyncio.get_event_loop()
    def _run():
        out_name = f"thumb_{uuid.uuid4().hex[:8]}.jpg"
        out_path = BASE_DIR / "thumbnails" / out_name
        out_path.parent.mkdir(exist_ok=True)
        try:
            from engines.thumbnail_engine import create_thumbnail
            create_thumbnail(req.video_path, str(out_path), req.ten_xe)
            return {"ok": True, "url": f"/files/{out_name}"}
        except Exception:
            pass
        try:
            import subprocess
            subprocess.run([
                config.FFMPEG_PATH, "-y", "-i", req.video_path,
                "-ss", "00:00:02", "-vframes", "1", str(out_path)
            ], capture_output=True, check=True)
            return {"ok": True, "url": f"/files/{out_name}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return await loop.run_in_executor(_executor, _run)


# Export platform
class ExportReq(BaseModel):
    video_path: str
    platform: str = "tiktok"

@app.post("/api/export")
async def api_export(req: ExportReq):
    loop = asyncio.get_event_loop()
    def _run():
        spec = config.EXPORT_SPECS.get(req.platform.lower(), config.EXPORT_SPECS["tiktok"])
        out_name = f"export_{req.platform}_{uuid.uuid4().hex[:8]}.mp4"
        out_path = BASE_DIR / "output" / out_name
        out_path.parent.mkdir(exist_ok=True)
        try:
            import subprocess
            subprocess.run([
                config.FFMPEG_PATH, "-y", "-i", req.video_path,
                "-vf", (f"scale={spec['width']}:{spec['height']}:"
                        f"force_original_aspect_ratio=decrease,"
                        f"pad={spec['width']}:{spec['height']}:(ow-iw)/2:(oh-ih)/2"),
                "-r", str(spec["fps"]), "-b:v", spec["bitrate"],
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac", "-b:a", "128k", str(out_path)
            ], capture_output=True, check=True)
            size_mb = round(out_path.stat().st_size / 1024 / 1024, 1)
            return {"ok": True, "url": f"/files/{out_name}", "filename": out_name, "size_mb": size_mb}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return await loop.run_in_executor(_executor, _run)


# Render full video
class RenderReq(BaseModel):
    video_path: str
    ten_xe: str
    mau_xe: str = ""
    loai_video: str = "Review xe"
    script: str = ""

@app.post("/api/render_video")
async def api_render_video(req: RenderReq):
    loop = asyncio.get_event_loop()
    def _run():
        out_name = f"render_{uuid.uuid4().hex[:8]}.mp4"
        out_path = BASE_DIR / "output" / out_name
        out_path.parent.mkdir(exist_ok=True)
        try:
            from engines.video_engine import create_video_with_text
            create_video_with_text(
                input_path=req.video_path, output_path=str(out_path),
                text=req.script or f"{req.ten_xe} - {req.mau_xe}",
                shop_name=config.SHOP_NAME, shop_hotline=config.SHOP_HOTLINE,
            )
        except Exception:
            import subprocess
            subprocess.run([
                config.FFMPEG_PATH, "-y", "-i", req.video_path,
                "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", str(out_path)
            ], capture_output=True, check=True)
        size_mb = round(out_path.stat().st_size / 1024 / 1024, 1)
        return {"ok": True, "url": f"/files/{out_name}", "filename": out_name, "size_mb": size_mb}
    try:
        return await loop.run_in_executor(_executor, _run)
    except Exception as e:
        raise HTTPException(500, str(e))


# Serve files
@app.get("/files/{path:path}")
def serve_file(path: str):
    for base in [BASE_DIR / "output", BASE_DIR / "temp",
                 BASE_DIR / "thumbnails", BASE_DIR / "captions"]:
        fp = base / path
        if fp.exists():
            return FileResponse(str(fp))
    raise HTTPException(404, "File not found")


# ── MUSIC LIBRARY ────────────────────────────────────────────────────
MUSIC_DIR = BASE_DIR / "music"
EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}

@app.get("/api/music_list")
def api_music_list():
    """Trả về danh sách nhạc trong thư mục music/"""
    tracks = []
    if MUSIC_DIR.exists():
        for f in sorted(MUSIC_DIR.iterdir()):
            if f.suffix.lower() in EXTS:
                tracks.append({
                    "name": f.stem,
                    "file": f.name,
                    "url": f"/music/{f.name}",
                    "ext": f.suffix.lower()
                })
    return {"tracks": tracks, "total": len(tracks)}

@app.get("/music/{filename}")
def serve_music(filename: str):
    """Serve file nhạc để nghe thử"""
    f = MUSIC_DIR / filename
    if not f.exists() or f.suffix.lower() not in EXTS:
            raise HTTPException(404, "File not found")
    media = "audio/mpeg" if f.suffix.lower() in {'.mp3'} else "audio/wav"
    return FileResponse(str(f), media_type=media)


# ── VOICE STYLE (Hoc giong & ngu dieu) ─────────────────────────────
VALID_SLOTS = ("person_1", "person_2", "person_3")

class VoiceSampleReq(BaseModel):
    text: str
    label: str = ""

class VoiceRenameReq(BaseModel):
    display_name: str

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
                "analyzed": p.get("analyzed", False),
                "tone": p.get("pattern", {}).get("tone", ""),
                "style_prompt": p.get("style_prompt", ""),
            })
        return {"profiles": result}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/voice_style/{slot}")
def vs_get(slot: str):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile
        return load_style_profile(slot)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/voice_style/{slot}/rename")
def vs_rename(slot: str, req: VoiceRenameReq):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile, save_style_profile
        p = load_style_profile(slot)
        p["display_name"] = req.display_name.strip()[:30]
        save_style_profile(p, slot)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/voice_style/{slot}/add_sample")
def vs_add_sample(slot: str, req: VoiceSampleReq):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import add_sample
        ok, msg = add_sample(req.text, req.label, slot)
        return {"ok": ok, "message": msg}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/voice_style/{slot}/sample/{idx}")
def vs_remove_sample(slot: str, idx: int):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import remove_sample
        ok, msg = remove_sample(idx, slot)
        return {"ok": ok, "message": msg}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/voice_style/{slot}/analyze")
async def vs_analyze(slot: str):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    loop = asyncio.get_event_loop()
    def _run():
        try:
            from engines.voice_style_engine import analyze_style
            from engines.ai_engine import get_ai_engine
            ai = get_ai_engine()
            result = analyze_style(slot, ai_engine=ai if ai.is_ready() else None)
            if "error" in result:
                return {"ok": False, "message": result["error"]}
            return {"ok": True, "pattern": result.get("pattern", {}),
                    "style_prompt": result.get("style_prompt", "")}
        except Exception as e:
            return {"ok": False, "message": str(e)}
    return await loop.run_in_executor(_executor, _run)

@app.post("/api/voice_style/{slot}/clear")
def vs_clear(slot: str):
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")
    try:
        from engines.voice_style_engine import load_style_profile, save_style_profile, _default_profile
        p = _default_profile(slot)
        save_style_profile(p, slot)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/voice_style/{slot}/add_from_file")
async def vs_add_from_file(slot: str, file: UploadFile = File(...), label: str = ""):
    """Upload video/audio → Whisper transcribe → thêm vào mẫu giọng điệu."""
    if slot not in VALID_SLOTS:
        raise HTTPException(400, "Invalid slot")

    # Lưu file tạm
    suffix = Path(file.filename).suffix.lower() if file.filename else ".mp4"
    tmp_path = Path(config.DATAABASE_DIR) / f"_vs_tmp_{uuid.uuid4().hex}{suffix}"
    try:
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        tmp_path.write_bytes(content)

        try:
            from engines.voice_style_engine import add_sample_from_video
            loop = asyncio.get_event_loop()
            ok, msg, transcript = await loop.run_in_executor(
                _executor,
                lambda: add_sample_from_video(str(tmp_path), label or Path(file.filename or "").stem[:40], slot)
            )
            if ok:
                return {"ok": True, "message": msg, "transcript": transcript}
            return {"ok": False, "message": msg, "transcript": ""}
        except Exception as e:
            return {"ok": False, "message": f"Loi transcribe: {e}", "transcript": ""}
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


# /api/config — trả về đúng key mà frontend cần
@app.get("/api/config")
def api_config():
    d = api_data()
    return {
        "xe_list":        d.get("vehicles", []),
        "mau_list":       d.get("colors", []),
        "loai_list":      d.get("types", []),
        "doi_tuong_list": d.get("audiences", []),
        "highlights":     d.get("highlights", []),
    }


# /api/score — chấm điểm viral
class ScoreReq(BaseModel):
    script: str
    ten_xe: str = ""

@app.post("/api/score")
async def api_score(req: ScoreReq):
    try:
        from engines.score_engine import calculate_score, format_score_report
        result = calculate_score(req.script, req.ten_xe)
        return {"ok": True, "score": result.get("total", 0),
                "score_text": format_score_report(result), "detail": result}
    except Exception as e:
        # Fallback: AI chấm điểm nếu score_engine fail
        try:
            import anthropic as _ant
            client = _ant.Anthropic(api_key=config.CLAUDE_API_KEY)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=200,
                messages=[{"role": "user", "content":
                    f"Cham diem viral (0-100) cho script TikTok xe dien nay, chi tra loi so va 1 dong nhan xet:\n{req.script[:500]}"}]
            )
            txt = msg.content[0].text.strip()
            import re as _re
            nums = _re.findall(r'\d+', txt)
            score = int(nums[0]) if nums else 70
            return {"ok": True, "score": score, "score_text": f"⭐ {score}/100 — {txt[:100]}"}
        except Exception as e2:
            return {"ok": False, "score": 0, "score_text": f"Loi: {e2}"}


# /api/check_duplicate — kiem tra trung lap
class DupReq(BaseModel):
    script: str = ""
    content: str = ""   # alias — frontend có thể gửi "content" thay vì "script"

@app.post("/api/check_duplicate")
async def api_check_duplicate(req: DupReq):
    try:
        from engines.duplicate_engine import check_duplicate, format_duplicate_result
        text = req.script or req.content
        result = check_duplicate(text)
        return {"ok": True, "is_duplicate": result.get("is_duplicate", False),
                "similarity": result.get("max_similarity", 0),
                "message": format_duplicate_result(result)}
    except Exception as e:
        return {"ok": True, "is_duplicate": False,
                "similarity": 0, "message": f"Khong the kiem tra: {e}"}



# Frontend
@app.get("/")
def frontend():
    p = BASE_DIR / "frontend" / "index.html"
    if p.exists():
        return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>frontend/index.html not found</h1>")


@app.get("/mobile")
def mobile():
    p = BASE_DIR / "frontend" / "mobile.html"
    if p.exists():
        return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>frontend/mobile.html not found</h1>")


def main():
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )

if __name__ == "__main__":
    main()
