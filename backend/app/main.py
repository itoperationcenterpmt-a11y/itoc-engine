import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .routers import auth, dashboard, admin, ingest, report, integrations, wifi, insight
from . import jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    weak = settings().jwt_secret in ("ganti-di-produksi", "ganti-dengan-string-acak-panjang") or len(settings().jwt_secret) < 32
    if weak and os.environ.get("ITOC_ENV", "").lower() == "production":
        raise RuntimeError("ITOC_JWT_SECRET lemah (contoh atau kurang dari 32 karakter). Server produksi menolak start. Isi string acak panjang di .env.")
    if weak:
        logging.getLogger("itoc").warning("ITOC_JWT_SECRET masih nilai contoh/pendek: token bisa dipalsukan. Isi dengan string acak panjang (min. 32 karakter) di .env.")
    if settings().run_scheduler:
        jobs.start()
    yield
    jobs.stop()


app = FastAPI(title="Dashboard IT Pelindo Multi Terminal API", version="1.0", lifespan=lifespan,
              docs_url="/docs" if settings().docs else None, redoc_url="/redoc" if settings().docs else None, openapi_url="/openapi.json" if settings().docs else None)
_origins = [o.strip() for o in settings().cors_origins.split(",") if o.strip() and o.strip() != "*"]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "X-API-Key"])
CSP = "default-src 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org; connect-src 'self'; font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    h = resp.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"   # origin saja ke situs lain (dibutuhkan OSM untuk tile peta)
    h["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    h["Content-Security-Policy"] = CSP
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    h["Cross-Origin-Resource-Policy"] = "same-origin"
    h["X-Permitted-Cross-Domain-Policies"] = "none"
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https":
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        h["Cache-Control"] = "no-store"
        h["Pragma"] = "no-cache"
    else:
        h["Cache-Control"] = "no-cache"      # file statis selalu divalidasi ulang (304 bila tidak berubah), supaya browser tidak memakai JS/CSS lama
    return resp
for r in (auth.router, dashboard.router, admin.router, integrations.router, ingest.router, report.router, wifi.router, insight.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True}


fe = Path(__file__).resolve().parent.parent / settings().frontend_dir
if fe.is_dir():
    app.mount("/", StaticFiles(directory=fe, html=True), name="frontend")
