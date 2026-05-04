import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.cv import CV
from app.models.user import User
from app.models.analysis import AnalysisResult
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.cv_parser import parse_cv
from app.services.generator import generate_cover_letter, generate_optimised_cv
from app.services.matcher import analyse_skill_gap, calculate_match_score

router = APIRouter(prefix="/analysis")


@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(
    payload: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(CV).where(CV.id == payload.cv_id))
    cv = result.scalar_one_or_none()

    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found.",
        )

    if cv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this CV.",
        )

    cv_parsed = await parse_cv(cv.extracted_text)
    match_result = await calculate_match_score(cv.extracted_text, payload.jd_text)
    skill_gap = await analyse_skill_gap(cv_parsed, payload.jd_text)
    optimised_cv = await generate_optimised_cv(cv_parsed, payload.jd_text, skill_gap)
    cover_letter = await generate_cover_letter(cv_parsed, payload.jd_text, {
        **match_result,
        **skill_gap,
    })

    analysis = AnalysisResult(
        user_id=current_user.id,
        cv_id=cv.id,
        job_id=payload.job_id,
        match_score=match_result["match_score"],
        matched_skills=skill_gap.get("matched_skills", []),
        missing_critical=skill_gap.get("missing_critical", []),
        missing_optional=skill_gap.get("missing_optional", []),
        recommendation_summary=skill_gap.get("recommendation_summary", ""),
        optimised_cv=optimised_cv,
        cover_letter=cover_letter,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return analysis


@router.get("/history", response_model=list[AnalysisResponse])
async def get_analysis_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.user_id == current_user.id)
        .order_by(AnalysisResult.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    if analysis.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this analysis.",
        )

    return analysis
