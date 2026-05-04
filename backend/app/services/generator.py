import json
import logging
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
)

str_parser = StrOutputParser()

# ---------------------------------------------------------------------------
# Structured JSON content block format
# ---------------------------------------------------------------------------
# Each block is a dict with "type" and "content" keys.
#   type: "heading"    -> bold, large text  (section titles)
#   type: "subheading" -> bold, normal text (job titles, project names)
#   type: "paragraph"  -> normal body text
#   type: "list"       -> content is a list of strings (bullet items)
#   type: "contact"    -> contact info line
#   type: "divider"    -> horizontal separator (content is empty string)
# ---------------------------------------------------------------------------

OPTIMISE_CV_PROMPT = PromptTemplate(
    input_variables=["cv_data", "jd_text", "skill_gap"],
    template="""You are an expert CV writer and ATS optimisation specialist.

Rewrite the candidate's CV to maximise their chances for the target role.

Candidate CV Data:
{cv_data}

Target Job Description:
{jd_text}

Skill Gap Analysis:
{skill_gap}

Instructions:
- Rewrite experience bullet points using action verbs and keywords from the job description
- Highlight the most relevant experience and achievements for this specific role
- Inject ATS-friendly keywords naturally throughout the CV without fabricating experience
- Emphasise matched skills prominently and frame transferable skills toward the missing ones
- Maintain honesty — do not invent qualifications or experience the candidate does not have

OUTPUT FORMAT (VERY IMPORTANT — follow exactly):
Return a JSON array of content blocks. Each block is an object with "type" and "content".
Available types:
  "heading"    — section titles (e.g. SUMMARY, SKILLS, EXPERIENCE, EDUCATION)
  "subheading" — job titles, project names, degree names
  "paragraph"  — normal body text
  "list"       — content MUST be an array of strings (bullet items)
  "contact"    — contact information line
  "divider"    — visual separator, content should be ""

Example structure:
[
  {{"type": "heading", "content": "CANDIDATE NAME"}},
  {{"type": "contact", "content": "email@example.com | +1-234-567-890 | linkedin.com/in/name"}},
  {{"type": "divider", "content": ""}},
  {{"type": "heading", "content": "SUMMARY"}},
  {{"type": "paragraph", "content": "Experienced software engineer with..."}},
  {{"type": "divider", "content": ""}},
  {{"type": "heading", "content": "SKILLS"}},
  {{"type": "list", "content": ["Python, TensorFlow, PyTorch", "Docker, Kubernetes, CI/CD"]}},
  {{"type": "divider", "content": ""}},
  {{"type": "heading", "content": "EXPERIENCE"}},
  {{"type": "subheading", "content": "Software Engineer | Company Name | Jan 2022 – Present"}},
  {{"type": "list", "content": ["Built scalable APIs...", "Improved performance by 40%..."]}},
  {{"type": "divider", "content": ""}},
  {{"type": "heading", "content": "EDUCATION"}},
  {{"type": "subheading", "content": "BS Computer Science | University Name"}},
  {{"type": "paragraph", "content": "CGPA: 3.74/4.00 | Graduation: 2025"}}
]

Return ONLY the JSON array, no other text.""",
)

COVER_LETTER_PROMPT = PromptTemplate(
    input_variables=["cv_data", "jd_text", "match_analysis"],
    template="""You are an expert professional writer specialising in cover letters.

Write a personalised, compelling cover letter for the candidate applying to this role.

Candidate CV Data:
{cv_data}

Target Job Description:
{jd_text}

Match Analysis:
{match_analysis}

Instructions:
- Address the letter professionally (use "Dear Hiring Manager" if no name is available)
- Open with a strong hook referencing the specific role and company if mentioned in the JD
- Highlight 2-3 of the candidate's most relevant achievements that align with the JD requirements
- Reference specific skills and experiences that match the role's key requirements
- Demonstrate enthusiasm and cultural fit based on the job description
- Close with a confident call to action
- Keep the tone formal yet personable
- Keep the length to approximately 300-400 words

OUTPUT FORMAT (VERY IMPORTANT — follow exactly):
Return a JSON array of content blocks. Each block is an object with "type" and "content".
Available types:
  "heading"   — for the candidate name at the top and "Cover Letter" title
  "contact"   — contact information line
  "paragraph" — each paragraph of the letter body
  "divider"   — visual separator, content should be ""

Example structure:
[
  {{"type": "heading", "content": "Cover Letter"}},
  {{"type": "divider", "content": ""}},
  {{"type": "paragraph", "content": "Dear Hiring Manager,"}},
  {{"type": "paragraph", "content": "I am writing to express my strong interest in the... This is the opening paragraph."}},
  {{"type": "paragraph", "content": "In my current role at... This is the body paragraph highlighting achievements."}},
  {{"type": "paragraph", "content": "I am particularly drawn to... This paragraph shows enthusiasm and cultural fit."}},
  {{"type": "paragraph", "content": "I would welcome the opportunity to discuss... This is the closing call to action."}},
  {{"type": "divider", "content": ""}},
  {{"type": "paragraph", "content": "Sincerely,"}},
  {{"type": "paragraph", "content": "Candidate Name"}}
]

Return ONLY the JSON array, no other text.""",
)


def _extract_json(raw: str) -> list[dict]:
    """Extract and parse JSON array from LLM output.

    Handles cases where the LLM wraps JSON in markdown code fences
    like ```json ... ``` or returns extra text around the array.
    """
    # Try direct parse first
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1).strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Try to find first [ ... last ]
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Fallback: return raw text as a single paragraph block
    logger.warning("Could not parse structured JSON from LLM output, using fallback.")
    return [{"type": "paragraph", "content": raw}]


async def generate_optimised_cv(
    cv_parsed: dict, jd_text: str, skill_gap: dict
) -> list[dict]:
    """Generate an optimised CV as structured JSON content blocks."""
    chain = OPTIMISE_CV_PROMPT | llm | str_parser
    try:
        raw = await chain.ainvoke(
            {
                "cv_data": json.dumps(cv_parsed, indent=2),
                "jd_text": jd_text,
                "skill_gap": json.dumps(skill_gap, indent=2),
            }
        )
        return _extract_json(raw)
    except Exception as e:
        logger.error(f"Error generating optimised CV: {e}")
        return []


async def generate_cover_letter(
    cv_parsed: dict, jd_text: str, match_analysis: dict
) -> list[dict]:
    """Generate a cover letter as structured JSON content blocks."""
    chain = COVER_LETTER_PROMPT | llm | str_parser
    try:
        raw = await chain.ainvoke(
            {
                "cv_data": json.dumps(cv_parsed, indent=2),
                "jd_text": jd_text,
                "match_analysis": json.dumps(match_analysis, indent=2),
            }
        )
        return _extract_json(raw)
    except Exception as e:
        logger.error(f"Error generating cover letter: {e}")
        return []
