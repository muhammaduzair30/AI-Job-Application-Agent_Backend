import json
import math

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.services.embeddings import embedding_model

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    max_retries=2,
)

EMPTY_GAP_ANALYSIS = {
    "matched_skills": [],
    "missing_critical": [],
    "missing_optional": [],
    "recommendation_summary": "",
}

SKILL_GAP_PROMPT = PromptTemplate(
    input_variables=["cv_skills", "jd_text"],
    template="""You are an expert career advisor and recruiter. Analyse the candidate's skills against the job description.

Candidate Skills:
{cv_skills}

Job Description:
{jd_text}

Return a JSON object with exactly these fields:
- "matched_skills": list of strings — skills the candidate has that match the JD requirements
- "missing_critical": list of strings — essential skills required by the JD that the candidate lacks
- "missing_optional": list of strings — nice-to-have skills mentioned in the JD that the candidate lacks
- "recommendation_summary": string — a brief actionable summary advising the candidate on how to improve their fit

Return ONLY valid JSON, no markdown formatting, no code blocks.""",
)

parser = JsonOutputParser()


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


async def calculate_match_score(cv_text: str, jd_text: str) -> dict:
    vectors = await embedding_model.aembed_documents([cv_text, jd_text])
    cv_vector, jd_vector = vectors[0], vectors[1]

    similarity = _cosine_similarity(cv_vector, jd_vector)
    match_score = int(round(max(0.0, min(1.0, similarity)) * 100))

    return {"match_score": match_score, "similarity": round(similarity, 4)}


async def analyse_skill_gap(cv_parsed: dict, jd_text: str) -> dict:
    try:
        skills_text = json.dumps(cv_parsed.get("skills", []))
        chain = SKILL_GAP_PROMPT | llm | parser
        result = await chain.ainvoke({"cv_skills": skills_text, "jd_text": jd_text})
        return {**EMPTY_GAP_ANALYSIS, **result}
    except Exception as e:
        error_msg = str(e)
        if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
            result = EMPTY_GAP_ANALYSIS.copy()
            result["recommendation_summary"] = (
                "The AI service is currently busy. We couldn't generate a detailed "
                "skill gap analysis right now, but your match score is still available based on our local algorithms."
            )
            return result
        return EMPTY_GAP_ANALYSIS.copy()
