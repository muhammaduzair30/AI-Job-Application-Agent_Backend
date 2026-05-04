# ⚙️ AIAA Backend Engine
### *Powered by FastAPI & Google Gemini AI*

This is the robust backend powering the **AI Job Application Agent**. It handles all AI processing, document parsing, and data management for the AIAA ecosystem.

---

## 🧠 AI Capabilities
- **Document RAG**: Retrieval-Augmented Generation for intelligent CV parsing.
- **Gemini Integration**: Uses Google's latest Gemini models for deep analysis and text generation.
- **Analysis Logic**: Complex algorithms to calculate matching scores and extract skill gaps.

---

## 🛠️ Tech Stack
- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL (via SQLAlchemy & Alembic)
- **AI Engine**: Google Generative AI (Gemini)
- **Containerization**: Docker & Docker Compose
- **Security**: JWT Authentication with Refresh Tokens

---

## 🚀 Setup & Installation

### Using Docker (Recommended)
1. Ensure Docker and Docker Compose are installed.
2. Build and start the services:
   ```bash
   docker-compose up --build
   ```

### Manual Setup
1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Setup `.env` file in the `backend/` folder (see `.env.example`).
4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 🗺️ API Documentation
Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📂 Architecture
- `app/api`: API endpoints and routing.
- `app/core`: Configuration, security, and AI service logic.
- `app/models`: Database schemas.
- `app/schemas`: Pydantic models for validation.
- `app/services`: Business logic and external integrations.
