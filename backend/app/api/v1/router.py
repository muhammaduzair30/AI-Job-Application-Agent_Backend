from fastapi import APIRouter

from app.api.v1.endpoints.analysis import router as analysis_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cv import router as cv_router
from app.api.v1.endpoints.job import router as job_router
from app.api.v1.endpoints.job_application import router as job_application_router

api_router = APIRouter()

# Auth router already carries prefix="/auth"; we add the canonical tag here.
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(cv_router, tags=["CV Management"])
api_router.include_router(analysis_router, tags=["Analysis"])
api_router.include_router(job_router, tags=["Jobs"])
api_router.include_router(job_application_router, prefix="/applications", tags=["Job Applications"])
