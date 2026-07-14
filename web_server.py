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

def main():
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("web_server:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
