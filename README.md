# Loan-processin-ai
# Intelligent Loan Document Processing Pipeline 🏦

An agentic pipeline built with LangGraph, Google Gemini Vision, FastAPI, Streamlit, and MongoDB Atlas to automate document classification, structured data extraction, cross-document validation, and credit underwriting.

---

## 🛠️ Tech Stack
* **Language & Orchestration:** Python 3.10+, LangGraph, LangChain
* **LLM / Perception:** Google Gemini 2.5 Flash API (Structured Output with Pydantic)
* **Backend:** FastAPI, Uvicorn
* **Database:** MongoDB Atlas (via Motor Async Driver)
* **Frontend:** Streamlit

---

## 🚀 Quickstart for Team Members

### 1. Clone & Setup Virtual Environment
```bash
git clone [https://github.com/](https://github.com/)<your-username>/<repo-name>.git
cd <repo-name>
python -m venv .venv
# Activate:
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 4. Run the Synthetic Document Generator
```bash
python generate_test_package.py
```

### 5. Launch Services
* **FastAPI Backend (Terminal 1):**
  ```bash
  uvicorn api:app --reload --port 8000
  ```
* **Streamlit UI (Terminal 2):**
  ```bash
  streamlit run ui.py
  ```
