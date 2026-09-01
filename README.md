# Intelligent Loan Document Processing Pipeline 🏦

An end-to-end multimodal agentic pipeline built with **LangGraph**, **Google Gemini Vision**, **FastAPI**, **Streamlit**, and **MongoDB Atlas** to automate document classification, structured data extraction, cross-document verification, policy risk scoring, and credit underwriting.

---

## 🛠️ Architecture & Tech Stack

* **Orchestration & Workflow:** LangGraph (StateGraph pipeline coordinating intake, validation, and underwriting)
* **LLM & Multimodal Vision:** Google Gemini (`gemini-2.5-flash`) via LangChain Structured Output
* **Backend API:** FastAPI, Uvicorn (StatReload async server)
* **Database & Persistence:** MongoDB Atlas (Async I/O via `motor`)
* **Underwriter Workbench:** Streamlit (Human-in-the-Loop field verification & historical compliance audit)
* **Document Processing:** PyMuPDF (`fitz`), Pillow (PDF rasterization & image preprocessing)

```text
[Borrower Documents (PDF/PNG)]
             │
             ▼
   [FastAPI Ingestion] (api.py)
             │
             ▼
 ┌────────────────────────────────────────────────────────┐
 │                   LangGraph Pipeline                   │
 │                                                        │
 │ 1. Intake & Extract (extractor.py + Gemini Vision)     │
 │    - Single-pass Classification + Schema Extraction    │
 │    - Normalization & Transaction Categorization        │
 │                                                        │
 │ 2. Validation & Policy Scoring (risk_scorer.py)        │
 │    - Cross-Document Identity & PAN Verification        │
 │    - DTI, FOIR, & Undisclosed EMI Math Calculations    │
 │    - Policy Engine (personal_loan_rules.json)          │
 │                                                        │
 │ 3. Explainable Underwriting (underwriter.py)           │
 │    - Synthesis: APPROVED / REVIEW / REJECT             │
 │    - Adverse Action Notices & Pre-Disbursal Conditions │
 └───────────────────────────┬────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [MongoDB Atlas]                   [Streamlit Workbench]
- Application State & Raw Docs      - Executive Summary & Anomaly Badges
- Human Verification Audit Logs     - Incomplete Doc Incremental Uploader
- Historical Compliance Lookup      - Human-in-the-Loop (HITL) Field Editor

├── api.py                       # FastAPI application endpoints & lifecycle handlers
├── ui.py                        # Streamlit underwriter operations dashboard
├── generate_test_package.py     # Synthetic borrower test suite generator
├── test_documents/              # Generated mock test documents (PDFs & PNGs)
├── src/
│   ├── config.py                # Environment configuration & model settings
│   ├── workflow.py              # LangGraph pipeline definition (StateGraph)
│   ├── agents/
│   │   ├── extractor.py         # Unified Multimodal Vision classification & extraction
│   │   ├── underwriter.py       # LLM credit reasoning & adverse action generator
│   │   └── llm_factory.py       # Google GenAI client factory with retry backoff
│   ├── database/
│   │   └── mongo.py             # Motor async MongoDB client & collections
│   ├── decision_engine/
│   │   ├── calculations.py      # DTI, net income, and EMI arithmetic calculations
│   │   ├── comparison.py        # Cross-document identity, employer, and PAN comparison
│   │   ├── extractors.py        # Pipeline payload entity resolvers
│   │   ├── policy_loader.py     # Dynamic underwriting rule loader
│   │   ├── risk_scorer.py       # Anomaly detection & composite risk scoring
│   │   └── personal_loan_rules.json # Underwriting policy configuration
│   ├── schemas/
│   │   ├── document_models.py   # Pydantic schemas for all financial/KYC documents
│   │   └── decision_models.py   # DecisionResult, Anomaly, and RiskFactor models
│   └── utils/
│       ├── assembly.py          # Missing document detection & applicant blocks
│       ├── normalizer.py        # String, PAN, and numerical data sanitization
│       └── pdf_utils.py         # Multi-page PDF to base64 image converter


git clone [https://github.com/Shankadude/Loan-processin-ai.git](https://github.com/Shankadude/Loan-processin-ai.git)
cd Loan-processin-ai
python -m venv .venv
1. Activate Virtual Environment:
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

2.Install Dependencies
pip install -r requirements.txt

3. Environment Configuration
Create a .env file in the root directory:

GOOGLE_API_KEY=your_gemini_api_key
MONGO_DETAILS=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/loan_db?retryWrites=true&w=majority
VISION_MODEL_NAME=gemini-2.5-flash
REASONING_MODEL_NAME=gemini-2.5-flash

5. Launch the System
Terminal 1 — FastAPI Backend Engine:

Bash
uvicorn api:app --reload --port 8000
Terminal 2 — Streamlit Underwriting Workbench:

Bash
streamlit run ui.py
Open http://localhost:8501 in your browser to access the workbench.
