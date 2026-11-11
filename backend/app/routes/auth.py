"""认证路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import auth_controller
from app.middlewares.auth import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, RefreshRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    return auth_controller.login(db, payload.email, payload.password)


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    return auth_controller.refresh(db, payload.refresh_token)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return auth_controller.user_payload(user)
