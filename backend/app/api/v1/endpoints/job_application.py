import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.cv import CV
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.user import User
from app.schemas.job_application import (
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
)

router = APIRouter()

@router.post("", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_job_application(
    application_in: JobApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cv_result = await db.execute(select(CV).where(CV.id == application_in.cv_id))
    cv = cv_result.scalar_one_or_none()
    if not cv or cv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CV not found or access denied")

    job_result = await db.execute(select(Job).where(Job.id == application_in.job_id))
    job = job_result.scalar_one_or_none()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Job not found or access denied")

    application = JobApplication(
        user_id=current_user.id,
        cv_id=application_in.cv_id,
        job_id=application_in.job_id,
        analysis_id=application_in.analysis_id,
        status=application_in.status,
        notes=application_in.notes,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    
    result = await db.execute(
        select(JobApplication)
        .options(joinedload(JobApplication.cv), joinedload(JobApplication.job))
        .where(JobApplication.id == application.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[JobApplicationResponse])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(JobApplication)
        .options(joinedload(JobApplication.cv), joinedload(JobApplication.job))
        .where(JobApplication.user_id == current_user.id)
        .order_by(JobApplication.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{application_id}", response_model=JobApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(JobApplication)
        .options(joinedload(JobApplication.cv), joinedload(JobApplication.job))
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
        
    if application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        
    return application


@router.patch("/{application_id}", response_model=JobApplicationResponse)
async def update_application(
    application_id: uuid.UUID,
    update_in: JobApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(JobApplication).where(JobApplication.id == application_id))
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
        
    if application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        
    if update_in.status is not None:
        application.status = update_in.status
    if update_in.notes is not None:
        application.notes = update_in.notes
    if update_in.applied_date is not None:
        application.applied_date = update_in.applied_date
        
    await db.commit()

    # Re-fetch with eagerly loaded relations so the response serializer
    # doesn't trigger a lazy-load on the async session (which would blow up).
    result = await db.execute(
        select(JobApplication)
        .options(joinedload(JobApplication.cv), joinedload(JobApplication.job))
        .where(JobApplication.id == application.id)
    )
    return result.scalar_one()


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(JobApplication).where(JobApplication.id == application_id))
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job application not found")
        
    if application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        
    await db.delete(application)
    await db.commit()
