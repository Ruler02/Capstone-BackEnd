"""Kumpulan seluruh sub-router aplikasi."""

from fastapi import APIRouter

from app.api import admin, auth, bpbd, pimpinan, public

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(public.router)
api_router.include_router(admin.router)
api_router.include_router(pimpinan.router)
api_router.include_router(bpbd.router)
