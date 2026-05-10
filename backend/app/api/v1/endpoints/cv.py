import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.cv import CV
from app.models.user import User
from app.schemas.cv import CVResponse
from app.services.embeddings import delete_vectors, embed_and_store
from app.services.file_handler import extract_text
from app.services.storage import upload_file_to_supabase, delete_file_from_supabase, generate_presigned_url

router = APIRouter(prefix="/cv")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {"pdf", "docx"}


@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    filename = file.filename or ""
    extension = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '.{extension}'. Accepted: .pdf, .docx",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10 MB limit.",
        )

    extracted_text = extract_text(filename, file_bytes)
    
    # Upload to Supabase Storage
    file_path = upload_file_to_supabase(file_bytes, filename, current_user.id)

    cv = CV(
        user_id=current_user.id,
        original_filename=filename,
        extracted_text=extracted_text,
        file_path=file_path,
    )
    db.add(cv)
    await db.commit()
    await db.refresh(cv)

    background_tasks.add_task(
        embed_and_store,
        text=extracted_text,
        doc_id=str(cv.id),
        metadata={"user_id": str(current_user.id), "type": "cv"},
    )

    return cv


@router.get("", response_model=list[CVResponse])
async def list_cvs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(CV).where(CV.user_id == current_user.id).order_by(CV.created_at.desc())
    )
    cvs = result.scalars().all()
    return cvs


@router.get("/{cv_id}", response_model=CVResponse)
async def get_cv(
    cv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cv = await db.get(CV, cv_id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    if cv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return cv


@router.get("/{cv_id}/download")
async def download_cv(
    cv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cv = await db.get(CV, cv_id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    if cv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if not cv.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No file associated with this CV")
        
    download_url = generate_presigned_url(cv.file_path)
    return {"download_url": download_url}


@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(
    cv_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cv = await db.get(CV, cv_id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    if cv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    # Delete file from storage
    if cv.file_path:
        delete_file_from_supabase(cv.file_path)
        
    await db.delete(cv)
    await db.commit()
    
    background_tasks.add_task(delete_vectors, str(cv_id))
    return None
