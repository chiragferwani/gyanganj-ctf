from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import time
import hashlib
from collections import defaultdict
try:
    from engine import SiddhaEngine          # when cwd is backend/
except ModuleNotFoundError:
    from backend.engine import SiddhaEngine  # when cwd is project root


app = FastAPI(title="Gyanganj")

# CORS — allow all for CTF
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_FLAG = os.environ.get("SECRET_FLAG", "KCTF{gy4ng4nj_4k4sh1c_7712c1e487ee}")
engine = SiddhaEngine(secret_flag=SECRET_FLAG)

# Rate limiting: max 120 requests per minute per IP
# (generous to support the 300-prompt pity challenge)
rate_limit_store: dict = defaultdict(list)
RATE_LIMIT = 120
RATE_WINDOW = 60  # seconds


class ChatRequest(BaseModel):
    message: str
    history: list = []   # list of {"role": str, "content": str}
    session_id: str = ""


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.get("/health")
async def health():
    return {"status": "awake", "realm": "Gyanganj"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    # --- Rate limiting ---
    ip = request.client.host
    now = time.time()
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < RATE_WINDOW]
    if len(rate_limit_store[ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many seekers approach at once. Return when the stars shift.",
        )
    rate_limit_store[ip].append(now)

    # --- Validate ---
    msg = req.message.strip()
    if not msg:
        raise HTTPException(
            status_code=400,
            detail="The void speaks. But I do not answer the void.",
        )
    if len(msg) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Such length serves only those who seek to overwhelm, not understand.",
        )

    # --- Session ---
    session_id = req.session_id or hashlib.md5(
        f"{ip}{time.time()}".encode()
    ).hexdigest()[:16]

    # --- Generate response ---
    response = engine.chat(message=msg, history=req.history)

    return ChatResponse(response=response, session_id=session_id)


@app.get("/")
async def root():
    # Serve the frontend index.html — check multiple possible locations
    _here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(_here, "static", "index.html"),      # Docker: frontend copied into static/
        os.path.join(_here, "..", "frontend", "index.html"),  # Local dev: project root layout
    ]
    for path in candidates:
        if os.path.isfile(path):
            return FileResponse(path)
    # Fallback JSON for API-only usage
    return JSONResponse(
        {
            "realm": "Gyanganj",
            "message": "You have reached the gate. Speak, seeker.",
            "endpoint": "/chat",
        }
    )


# Mount static files (frontend) — must come AFTER route definitions
_here = os.path.dirname(os.path.abspath(__file__))
_static_candidates = [
    os.path.join(_here, "static"),           # Docker path
    os.path.join(_here, "..", "frontend"),   # Local dev path
]
for _sd in _static_candidates:
    if os.path.isdir(_sd):
        app.mount("/static", StaticFiles(directory=_sd), name="static")
        break
