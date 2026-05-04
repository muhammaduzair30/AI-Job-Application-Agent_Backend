# AIAA Backend Audit Report

## 1. PROJECT STRUCTURE
**Status:** <span style="color:orange">WARNING</span>

**Observations:**
- The overall directory structure follows standard FastAPI patterns (`api`, `core`, `db`, `models`, `schemas`, `services`).
- Required `__init__.py` files are present in all necessary module directories.
- **Missing Files:** Based on the presence of `app/models/job.py` and `app/schemas/job.py`, there is a missing `app/api/v1/endpoints/job.py` file to handle job description CRUD operations.
- The `app/api/v1/router.py` does not include any router for job descriptions.

## 2. API ENDPOINTS AUDIT
**Status:** <span style="color:red">FAIL</span>

**Endpoints Found:**
- `POST /api/v1/auth/register` (Public) - Creates a new user account.
- `POST /api/v1/auth/login` (Public) - Authenticates a user and returns a JWT token.
- `GET /api/v1/auth/me` (Protected) - Returns current authenticated user details.
- `POST /api/v1/cv/upload` (Protected) - Uploads a CV, parses text, stores in DB, and generates embeddings in Pinecone.
- `POST /api/v1/analysis/run` (Protected) - Takes a `cv_id` and raw `jd_text`, runs the entire analysis pipeline, and returns the result without saving.

**Identified Issues:**
- **Incomplete / Missing Endpoints:** There are no endpoints to create, read, update, or delete `Job` entities, even though the database model is defined.
- **Results Retrieval:** There is no endpoint to retrieve historical analysis results. The `/analysis/run` endpoint performs the analysis on-the-fly and does not persist the results (e.g., match score, cover letter, optimised CV) to the database.
- **CV Management:** Missing endpoints to list a user's uploaded CVs (`GET /api/v1/cv`), retrieve a specific CV, or delete a CV.

## 3. DATABASE AUDIT
**Status:** <span style="color:green">PASS</span>

**Observations:**
- **Models Defined:** `User`, `CV`, and `Job` are correctly defined using SQLAlchemy 2.0 paradigms (`Mapped`, `mapped_column`).
- **Fields:** Field definitions are correct. Foreign keys to `users.id` on `CV` and `Job` models are appropriately enforced.
- **Relationships:** The `User` model correctly defines reverse relationships via `backref="cvs"` and `backref="jobs"`.
- **Alembic Configuration:** All models (`User`, `CV`, `Job`) are successfully imported in `alembic/env.py`, ensuring migrations will track schema changes for all entities. Async migration logic is correctly implemented.

## 4. SERVICES AUDIT
**Status:** <span style="color:red">FAIL</span>

**Service Functions & Findings:**
- `cv_parser.py` (`parse_cv`): Parses extracted CV text using an LLM.
- `embeddings.py` (`embed_and_store`, `search_similar`, `delete_vectors`): Handles Pinecone vector generation and retrieval.
- `file_handler.py` (`extract_text`, `extract_text_from_pdf`, `extract_text_from_docx`): Synchronous text extraction from PDF and DOCX files.
- `generator.py` (`generate_optimised_cv`, `generate_cover_letter`): Generates rewritten CVs and cover letters via an LLM.
- `matcher.py` (`calculate_match_score`, `analyse_skill_gap`): Performs cosine similarity checks and LLM-based gap analyses.

**Critical Issues Identified:**
- **Synchronous Blocking of Event Loop:** The `analysis/run` endpoint is an `async def` function, but it calls `parse_cv`, `calculate_match_score`, `analyse_skill_gap`, `generate_optimised_cv`, and `generate_cover_letter` directly. All of these service functions make **synchronous** API calls (via `.invoke()` and `.embed_documents()`) to the Google Generative AI API. This will severely block the FastAPI event loop, causing requests to hang for other users.
- **Unused ThreadPoolExecutor:** `analysis.py` defines `executor = ThreadPoolExecutor(max_workers=4)` on line 19, but completely fails to use it in the endpoint (e.g., via `run_in_threadpool` or `asyncio.get_running_loop().run_in_executor`).
- **Missing Async Conversions:** The Langchain integrations should be using their asynchronous counterparts (e.g., `.ainvoke()`, `.aembed_documents()`) to be native to the async architecture.
- **Error Handling:** `generator.py` lacks error handling entirely. Failures in the LLM call will crash the request with a 500 status without a graceful fallback.

## 5. SECURITY AUDIT
**Status:** <span style="color:orange">WARNING</span>

**Observations:**
- **JWT Implementation:** The `security.py` file has a complete JWT implementation including secure password hashing (bcrypt), token creation, and decoding.
- **Protected Routes:** All routes that require authentication correctly use `Depends(get_current_active_user)` to validate tokens and ensure users are active.

**Security Gaps Identified:**
- **CORS Configuration:** In `main.py`, CORS is configured with `allow_origins=["*"]`. This is insecure for production and should be constrained to explicit frontend origins.
- **Rate Limiting:** No rate limiting is implemented. Endpoints that trigger expensive LLM generation (`/analysis/run`) are exposed to abuse, which could quickly drain API quotas.

## 6. MISSING FUNCTIONALITY
**Status:** <span style="color:red">FAIL</span>

**Expected Features Comparison:**
- User registration and login: ✓ **Implemented**
- CV upload with text extraction: ✓ **Implemented**
- Job description input: ❌ **Incomplete** (Takes raw `jd_text` directly in the analysis run payload, but doesn't utilise the `Job` model to store job descriptions).
- CV to JD matching with score: ✓ **Implemented** (within `/analysis/run`)
- Skill gap analysis: ✓ **Implemented** (within `/analysis/run`)
- CV optimisation generation: ✓ **Implemented** (within `/analysis/run`)
- Cover letter generation: ✓ **Implemented** (within `/analysis/run`)
- Results retrieval endpoint: ❌ **Missing** (Analysis is executed on-the-fly and results are returned immediately but never persisted. Users cannot retrieve past analyses).

## 7. DEPLOYMENT READINESS
**Status:** <span style="color:green">PASS</span>

**Observations:**
- **Dockerfile:** Correctly implemented with multi-stage layer caching for dependencies, exposing port 8000, and running Uvicorn.
- **docker-compose.yml:** Complete and maps required volumes and ports, with standard PostgreSQL parameters set.
- **.env.example:** Contains all required environment variables properly documented, providing a solid template for local/production secrets.
- **Alembic:** Migrations structure is intact and ready.
