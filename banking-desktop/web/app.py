import sys, os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db.session import init_db
from web.routers import auth, accounts, transactions, loans, ai

app = FastAPI(
    title="NexaBank Web Application",
    description="Next-generation intelligent banking platform with AI assistant & multi-account financial management.",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static & Templates
web_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(web_dir / "templates"))

# Include API Routers
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(loans.router)
app.include_router(ai.router)

@app.on_event("startup")
def on_startup():
    try:
        init_db()
        print("[INFO] Database initialized successfully.")
    except Exception as e:
        print(f"[WARNING] Database startup notice: {e}")

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "NexaBank Web API", "timestamp": "2026-08-26"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=True)
