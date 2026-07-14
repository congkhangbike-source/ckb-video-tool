"""
CKB Video Tool - FastAPI Web Server
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
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "--quiet"])
    from fastapi import FastAPI, UploadFile, File, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn

# Try importing AI engine
try:
    import config
    from engines.ai_engine import get_ai_engine, reload_engine
    AI_AVAILABLE = True
except Exception as e:
    AI_AVAILABLE = False
    print(f"AI engine not loaded: {e}")

app = FastAPI(title="CKB Video Tool")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _serve_html(filename: str) -> HTMLResponse:
    """Try pages/ then frontend/ directories"""
    for d in ["pages", "frontend"]:
        p = BASE_DIR / d / filename
        if p.exists():
            return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse(f"<h1>{filename} not found</h1>", status_code=404)

@app.get("/")
def index():
    return _serve_html("index.html")

@app.get("/mobile")
def mobile():
    return _serve_html("mobile.html")

@app.get("/config.js")
def config_js():
    for d in ["pages", "frontend"]:
        p = BASE_DIR / d / "config.js"
        if p.exists():
            return FileResponse(p, media_type="application/javascript")
    return JSONResponse({"error": "config.js not found"}, status_code=404)


class GenerateRequest(BaseModel):
    ten_xe: str = ""
    mau_xe: str = ""
    loai_video: str = "Review xe"
    doi_tuong: str = "Hoc sinh / Sinh vien"
    diem_noi_bat: str = ""
    thoi_luong: str = "30 giay"
    platforms: list = ["TikTok", "Facebook"]

class ChatRequest(BaseModel):
    messages: list
    system: str = ""


@app.get("/api/status")
def api_status():
    ai_ready = False
    if AI_AVAILABLE:
        try:
            ai_ready = get_ai_engine().is_ready()
        except Exception:
            pass
    return {"status": "ok", "ai_ready": ai_ready, "ai_available": AI_AVAILABLE, "version": "2.0.0"}

@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    if not AI_AVAILABLE:
        return {"error": "AI engine not available"}
    try:
        engine = get_ai_engine()
        if not engine.is_ready():
            return {"error": "API key chua duoc cau hinh. Set ANTHROPIC_API_KEY"}
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, lambda: engine.generate_content(
            ten_xe=req.ten_xe, mau_xe=req.mau_xe, loai_video=req.loai_video,
            doi_tuong=req.doi_tuong, diem_noi_bat=req.diem_noi_bat,
            thoi_luong=req.thoi_luong, platforms=req.platforms,
        ))
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    if not AI_AVAILABLE:
        last_msg = req.messages[-1].get("content", "") if req.messages else ""
        return {"reply": f"[Demo] {last_msg[:50]}..."}
    try:
        engine = get_ai_engine()
        if not engine.is_ready():
            return {"reply": "API key chua cau hinh"}
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(_executor, lambda: engine.chat(
            messages=req.messages,
            system=req.system or "Ban la tro ly ban hang thong minh cua Cong Khang Bike tai Hai Phong."
        ))
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Loi: {str(e)}"}

@app.get("/api/products")
def api_products():
    try:
        db_file = BASE_DIR / "database" / "vehicles.json"
        if db_file.exists():
            data = json.loads(do_file.read_text(encoding="utf-8"))
            return {"products": data.get("xe_dien", [])}
    except Exception:
        pass
    return {"products": [
        {"ten": "Vinfast Ludo", "gia": 15900000, "loai": "xe_may_dien"},
        {"ten": "Vinfast Evo 200", "gia": 21900000, "loai": "xe_may_dien"},
        {"ten": "Dat Bike Weaver 200", "gia": 39900000, "loai": "xe_may_dien"},
        {"ten": "VinFast Klara S", "gia": 21500000, "loai": "xe_dap_dien"},
    ]}

@app.post("/api/reload-key")
async def reload_key(data: dict):
    new_key = data.get("api_key", "")
    if not new_key:
        return {"success": False, "error": "Khong co API key"}
    if AI_AVAILABLE:
        try:
            reload_engine()
            os.environ["ANTHROPIC_API_KEY"] = new_key
            engine = get_ai_engine()
            return {"success": engine.is_ready()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "AI engine not available"}


def main():
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("web_server:app", host="0.0.0.0", port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
