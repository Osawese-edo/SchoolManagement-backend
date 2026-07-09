import os
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException, BadRequestException
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, SetupStatusResponse, SetupAdminRequest
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.sse_manager import sse_manager
from app.services.log_helper import log_action
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        result = service.login(data.email, data.password)
    except ValueError as e:
        raise UnauthorizedException(detail=str(e))

    user = db.query(User).filter(User.email == data.email).first()
    if user:
        log_action(db, user, "Logged in", "auth")

    secure_cookie = os.getenv("ENV", "development") == "production"
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )
    return TokenResponse(access_token=result["access_token"])


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    secure_cookie = os.getenv("ENV", "development") == "production"
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise UnauthorizedException(detail="No refresh token")
    service = AuthService(db)
    try:
        result = service.refresh(refresh_token)
    except ValueError as e:
        raise UnauthorizedException(detail=str(e))

    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )
    return TokenResponse(access_token=result["access_token"])


@router.get("/me", response_model=UserResponse)
@limiter.limit("60/minute")
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/logout")
@limiter.limit("30/minute")
def logout(request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    service.logout(current_user.id)
    log_action(db, current_user, "Logged out", "auth")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.get("/setup-status", response_model=SetupStatusResponse)
def setup_status(db: Session = Depends(get_db)):
    cached = sse_manager.admin_exists
    if cached is not None:
        return SetupStatusResponse(admin_exists=cached)
    exists = db.query(User).filter(User.role == "admin").first() is not None
    sse_manager.admin_exists = exists
    return SetupStatusResponse(admin_exists=exists)


@router.get("/setup-status/stream")
async def setup_status_stream(db: Session = Depends(get_db)):
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        await sse_manager.subscribe(queue)
        try:
            cached = sse_manager.admin_exists
            if cached is None:
                cached = db.query(User).filter(User.role == "admin").first() is not None
                sse_manager.admin_exists = cached
            yield f"event: setup-status-changed\ndata: {json.dumps({'admin_exists': cached})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await sse_manager.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/setup-admin")
@limiter.limit("5/minute")
async def setup_admin(request: Request, data: SetupAdminRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        service.create_first_admin(data.email, data.password, data.full_name)
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    await sse_manager.update_admin_exists(True)
    return {"message": "Admin user created successfully"}
