import os
import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth
from app.api.admin import (
    activity_logs as admin_activity_logs,
    blog as admin_blog,
    content as admin_content,
    dashboard,
    form_fields as admin_form_fields,
    gallery as admin_gallery,
    leads as admin_leads,
    sections as admin_sections,
    services as admin_services,
    syllabus_import as admin_syllabus_import,
    system as admin_system,
    testimonials as admin_testimonials,
    upload as admin_upload,
    users as admin_users,
)
from app.api.public import (
    blog as public_blog,
    config,
    content,
    form_fields,
    gallery,
    leads,
    sections as public_sections,
    services,
    testimonials,
    theme as public_theme,
)
from app.api.school import routes as school_routes
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.rate_limit import limiter

logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()))
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="DESTINED CHAMPIONS FOUNDATION API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    origins = settings.cors_origins.copy()
    if settings.cors_origins_extra:
        origins.extend(o.strip() for o in settings.cors_origins_extra.split(",") if o.strip())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    if os.path.isdir(upload_dir):
        app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    @app.on_event("startup")
    def init_startup():
        try:
            from app.db.session import SessionLocal
            from app.models.user import User
            from app.services.sse_manager import sse_manager

            db = SessionLocal()
            try:
                admin_exists = db.query(User).filter(User.role == "admin").first() is not None
                sse_manager.admin_exists = admin_exists
            finally:
                db.close()
        except Exception as e:
            logger.warning("Could not check admin existence on startup: %s", e)

        try:
            from app.db.session import SessionLocal
            from app.models.site_content import SiteContent
            db = SessionLocal()
            try:
                svg = db.query(SiteContent).filter(
                    SiteContent.section == "contact",
                    SiteContent.field_key == "logo_svg",
                    SiteContent.is_active == True,
                ).first()
                if svg and svg.field_value:
                    logo_path = os.path.join(upload_dir, "logo.svg")
                    with open(logo_path, "w", encoding="utf-8") as f:
                        f.write(svg.field_value)
            finally:
                db.close()
        except Exception as e:
            logger.warning("Could not sync logo.svg from DB: %s", e)

    # ── Security & Request-ID middleware ─────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-src 'self' https://www.google.com; object-src 'none'; base-uri 'self'; form-action 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    # ── Global exception handlers ───────────────────────────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": exc.error_code,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        ref_id = str(uuid.uuid4())
        logger.exception("Unhandled exception [ref=%s]: %s", ref_id, exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "A technical error occurred. Please contact the technical team.",
                "error_code": "INTERNAL_ERROR",
                "reference_id": ref_id,
            },
        )

    public_prefix = "/api"
    app.include_router(content.router, prefix=public_prefix, tags=["Public - Content"])
    app.include_router(services.router, prefix=public_prefix, tags=["Public - Services"])
    app.include_router(gallery.router, prefix=public_prefix, tags=["Public - Gallery"])
    app.include_router(testimonials.router, prefix=public_prefix, tags=["Public - Testimonials"])
    app.include_router(leads.router, prefix=public_prefix, tags=["Public - Leads"])
    app.include_router(config.router, prefix=public_prefix, tags=["Public - Config"])
    app.include_router(form_fields.router, prefix=public_prefix, tags=["Public - Form Fields"])
    app.include_router(public_blog.router, prefix=public_prefix, tags=["Public - Blog"])
    app.include_router(public_sections.router, prefix=public_prefix, tags=["Public - Sections"])
    app.include_router(public_theme.router, prefix=public_prefix, tags=["Public - Theme"])

    auth_prefix = "/api/auth"
    app.include_router(auth.router, prefix=auth_prefix, tags=["Authentication"])

    admin_prefix = "/api/admin"
    app.include_router(dashboard.router, prefix=admin_prefix, tags=["Admin - Dashboard"])
    app.include_router(admin_content.router, prefix=admin_prefix, tags=["Admin - Content"])
    app.include_router(admin_services.router, prefix=admin_prefix, tags=["Admin - Services"])
    app.include_router(admin_gallery.router, prefix=admin_prefix, tags=["Admin - Gallery"])
    app.include_router(admin_testimonials.router, prefix=admin_prefix, tags=["Admin - Testimonials"])
    app.include_router(admin_leads.router, prefix=admin_prefix, tags=["Admin - Leads"])
    app.include_router(admin_users.router, prefix=admin_prefix, tags=["Admin - Users"])
    app.include_router(admin_upload.router, prefix=admin_prefix, tags=["Admin - Upload"])
    app.include_router(admin_form_fields.router, prefix=admin_prefix, tags=["Admin - Form Fields"])
    app.include_router(admin_blog.router, prefix=admin_prefix, tags=["Admin - Blog"])
    app.include_router(admin_sections.router, prefix=admin_prefix, tags=["Admin - Sections"])
    app.include_router(admin_system.router, prefix=admin_prefix, tags=["Admin - System"])
    app.include_router(admin_syllabus_import.router, prefix=admin_prefix, tags=["Admin - Syllabus Import"])
    app.include_router(admin_activity_logs.router, prefix=admin_prefix, tags=["Admin - Activity Logs"])

    school_prefix = "/api/school"
    app.include_router(school_routes.router, prefix=school_prefix, tags=["School"])

    @app.get("/health")
    def health():
        return {"status": "healthy", "service": "DESTINED CHAMPIONS FOUNDATION API"}

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(backend_dir, "static")

    admin_static = os.path.join(static_dir, "admin")
    if os.path.isdir(admin_static):
        app.mount("/admin", StaticFiles(directory=admin_static, html=True), name="admin")

    main_static = os.path.join(static_dir, "main-site")
    if os.path.isdir(main_static):
        assets_dir = os.path.join(main_static, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="main-assets")

        @app.get("/{full_path:path}")
        async def serve_main_spa(full_path: str = ""):
            if ".." in full_path or full_path.startswith("/") or full_path.startswith("\\"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            path = full_path or "index.html"
            file_path = os.path.join(main_static, path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(main_static, "index.html"))

    return app


app = create_app()
