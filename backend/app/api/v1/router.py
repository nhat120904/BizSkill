from fastapi import APIRouter
from app.api.v1.endpoints import (
    channels, videos, segments, search, 
    categories, auth, users, admin
)

api_router = APIRouter()

# Public endpoints
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(segments.router, prefix="/segments", tags=["segments"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Protected endpoints
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Admin endpoints
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(channels.router, prefix="/admin/channels", tags=["admin"])
api_router.include_router(videos.router, prefix="/admin/videos", tags=["admin"])
