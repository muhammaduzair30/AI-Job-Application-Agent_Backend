from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
)

EMPTY_STRUCTURE = {
    "full_name": "",
    "email": "",
    "phone": "",
    "skills": [],
    "experience": [],
    "education": [],
    "projects": [],
    "summary": "",
}

CV_PARSE_PROMPT = PromptTemplate(
    input_variables=["cv_text"],
    template="""You are an expert CV/resume parser. Extract structured information from the following CV text.

Return a JSON object with exactly these fields:
- "full_name": string
- "email": string
- "phone": string
- "skills": list of strings
- "experience": list of objects with keys "title", "company", "duration", "description"
- "education": list of objects with keys "degree", "institution", "year"
- "projects": list of objects with keys "name", "description", "technologies" (list of strings)
- "summary": string (a brief professional summary)

If a field cannot be determined from the CV, use an empty string or empty list as appropriate.
Return ONLY valid JSON, no markdown formatting, no code blocks.

CV Text:
{cv_text}""",
)

parser = JsonOutputParser()


async def parse_cv(extracted_text: str) -> dict:
    try:
        chain = CV_PARSE_PROMPT | llm | parser
        result = await chain.ainvoke({"cv_text": extracted_text})
        return {**EMPTY_STRUCTURE, **result}
    except Exception:
        return EMPTY_STRUCTURE.copy()
