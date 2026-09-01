# Loan Processing using Generative AI

## 📌 Overview

**Loan Processing using Generative AI** is an AI-assisted loan document processing and decision-support system designed to automate the verification, comparison, calculation, risk assessment, and final decision-making stages of a loan application.

The system processes information extracted from multiple loan-related documents such as:

* Loan Application
* PAN Card
* Payslips
* Bank Statements
* Form 16
* Other supporting financial documents

Instead of relying only on individual document extraction, the system performs **cross-document verification** to identify inconsistencies, undisclosed liabilities, income mismatches, and other potential risk indicators.

The architecture separates document comparison, deterministic financial calculations, risk analysis, and final decision-making into independent modules.

---

# 🎯 Problem Statement

Traditional loan processing requires manual verification of information across multiple documents.

A loan applicant may provide different values for:

* Monthly income
* Employer details
* Applicant identity
* Existing EMIs
* Liabilities
* Employment information

Manually comparing these values across documents is:

* Time-consuming
* Error-prone
* Difficult to scale
* Dependent on manual review
* Vulnerable to missed inconsistencies

The proposed system uses Generative AI and deterministic rule-based calculations to automate this process.

---

# 🎯 Objectives

The major objectives of the system are:

1. Automate extraction and processing of loan documents.
2. Compare declared information with verified information.
3. Detect inconsistencies across multiple documents.
4. Calculate verified income and financial obligations.
5. Calculate financial indicators such as DTI.
6. Detect anomalies and potential risks.
7. Apply predefined loan eligibility and risk policies.
8. Generate an explainable final loan recommendation.
9. Store processing results in MongoDB Atlas.
10. Reduce manual effort in loan underwriting.

---

# 🏗️ System Architecture

```text
                  ┌──────────────────────────┐
                  │      Loan Documents      │
                  │                          │
                  │  • Loan Application      │
                  │  • PAN                   │
                  │  • Payslips              │
                  │  • Bank Statements       │
                  │  • Form 16               │
                  └────────────┬─────────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │ Document Processing Layer│
                  │                          │
                  │ OCR / VLM / Extraction   │
                  └────────────┬─────────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │      MongoDB Atlas        │
                  │                          │
                  │ Extracted Application    │
                  │ Data / JSON              │
                  └────────────┬─────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │       Comparison Engine        │
              │                                │
              │ • Identity Comparison          │
              │ • Income Comparison            │
              │ • Employer Comparison           │
              │ • Liability Comparison          │
              │ • Semantic Comparison           │
              │ • Anomaly Detection             │
              └───────────────┬────────────────┘
                              │
                              │ ComparisonResult
                              ▼
              ┌────────────────────────────────┐
              │      Step 5 Calculation        │
              │                                │
              │ • calculate_income()            │
              │ • calculate_obligations()       │
              │ • calculate_statement_metrics()│
              │ • calculate_eligibility()       │
              └───────────────┬────────────────┘
                              │
                              ▼
              ┌────────────────────────────────┐
              │      Step 6 Risk Engine        │
              │                                │
              │ • Risk Scoring                 │
              │ • Anomaly Classification       │
              │ • Policy Evaluation            │
              │ • Risk Level                   │
              └───────────────┬────────────────┘
                              │
                              ▼
              ┌────────────────────────────────┐
              │       Decision Engine          │
              │                                │
              │ • Combine Results              │
              │ • Final Recommendation         │
              │ • Audit Notes                  │
              └───────────────┬────────────────┘
                              │
                              ▼
                  ┌──────────────────────────┐
                  │      Final Decision      │
                  │                          │
                  │ • Risk Score             │
                  │ • Risk Level             │
                  │ • Recommendation         │
                  │ • Reasons                │
                  │ • Audit Notes            │
                  └────────────┬─────────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │      MongoDB Atlas       │
                  │                          │
                  │   Final Loan Decision    │
                  └──────────────────────────┘
```

---

# 🔄 Processing Pipeline

The complete processing flow is:

```text
Documents
   ↓
Extraction
   ↓
MongoDB
   ↓
Comparison Engine
   ↓
ComparisonResult
   ↓
Step 5 Financial Calculations
   ↓
Step 6 Risk & Anomaly Analysis
   ↓
Decision Engine
   ↓
FinalDecision
   ↓
MongoDB
```

---

# 🔍 Comparison Engine

The Comparison Engine is responsible for comparing information declared by the applicant against information verified from supporting documents.

## Major comparison categories

### 1. Identity Verification

Compares:

* Applicant name
* PAN
* Date of birth
* Other identity information

Example:

```text
Declared Name: Prachi Hivarkar
PAN Name:      Prachi Hivarkar

Result: MATCH
```

---

### 2. Income Verification

The engine compares declared income against income obtained from supporting financial documents.

Example:

```text
Declared Monthly Income: ₹60,000
Verified Monthly Income: ₹48,000

Difference: ₹12,000

Result: INCOME_MISMATCH
```

---

### 3. Employer Verification

Employer information can be compared across:

* Loan application
* Payslip
* Form 16
* Bank statement

---

### 4. Liability Verification

Existing liabilities and EMIs are identified from available documents and bank transactions.

The engine can detect cases such as:

```text
Declared EMI: ₹5,000

Bank Statement:
Detected EMI: ₹15,000

Result:
UNDISCLOSED_LIABILITY
```

---

### 5. Semantic Comparison

Generative AI can be used to identify inconsistencies that cannot be detected using simple exact-value comparison.

For example:

```text
Loan Application:
Employment Type = Permanent

Payslip:
Employment Type = Contract

Semantic Result:
EMPLOYMENT_STATUS_MISMATCH
```

---

# 🧮 Step 5 – Financial Calculation Engine

Step 5 performs deterministic calculations using the verified information produced by the Comparison Engine.

The calculation layer does **not independently fetch documents again**.

Instead:

```text
Comparison Engine
       ↓
ComparisonResult
       ↓
Step 5 Calculation
```

This keeps the architecture modular and avoids duplicate document processing.

---

## Income Calculation

Implemented using:

```python
calculate_income()
```

It can use:

* Declared monthly net income
* Verified monthly net income
* Average salary credit from bank statements

Example:

```text
Declared Income       = ₹60,000
Verified Income       = ₹55,000
Average Salary Credit = ₹54,500
```

The result is stored as a calculation dictionary.

---

## Obligation Calculation

Implemented using:

```python
calculate_obligations()
```

It evaluates existing financial obligations such as:

* Existing EMIs
* Detected liabilities
* Declared liabilities
* Other recurring obligations

---

## Statement Metrics

Implemented using:

```python
calculate_statement_metrics()
```

It calculates useful financial indicators from bank statement data, such as:

* Average salary credit
* Transaction statistics
* EMI transactions
* Financial activity indicators

---

## Eligibility Calculation

Implemented using:

```python
calculate_eligibility()
```

Eligibility rules can be based on predefined policies such as:

* Minimum verified income
* Maximum DTI
* Maximum loan exposure
* Employment conditions
* Liability conditions
* Risk level

---

# ⚠️ Step 6 – Risk and Anomaly Engine

The Step 6 layer evaluates the results generated by the Comparison Engine and Step 5.

Potential anomalies include:

```text
INCOME_OVERSTATED
INCOME_MISMATCH
UNDISCLOSED_LIABILITY
EMPLOYER_MISMATCH
IDENTITY_MISMATCH
HIGH_DTI
UNUSUAL_TRANSACTION_PATTERN
```

The system can assign:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

risk levels.

---

# 📊 DTI Calculation

Debt-to-Income ratio is an important financial indicator.

```text
DTI = Total Monthly Debt Obligations
      -------------------------------- × 100
          Verified Monthly Income
```

Example:

```text
Verified Income = ₹50,000
Monthly EMI     = ₹20,000

DTI = (20,000 / 50,000) × 100
    = 40%
```

The resulting DTI can be evaluated against configured policies.

---

# 🧠 Generative AI Usage

Generative AI is primarily used where semantic understanding is required.

Possible applications include:

* Semantic document comparison
* Inconsistency detection
* Anomaly explanation
* Risk reasoning
* Audit-note generation
* Natural-language explanation of decisions

The system does **not rely on an LLM for deterministic financial arithmetic**.

For example:

```text
LLM
 ↓
Identify relevant information
 ↓
Structured comparison
 ↓
Deterministic calculation
 ↓
Policy evaluation
```

This improves reliability and explainability.

---

# 🔐 Policy-Based Decision Making

Business rules should be maintained separately from the AI reasoning layer.

Example:

```yaml
income:
  minimum_verified_income: 25000

dti:
  maximum_allowed: 50

risk:
  high_risk_threshold: 70
```

The policy layer allows loan rules to be modified without changing the core processing pipeline.

---

# 🗄️ MongoDB Integration

MongoDB Atlas is used as the persistence layer.

The database can contain:

```text
Loan Application
      │
      ├── Extracted Data
      │
      ├── Comparison Result
      │
      ├── Financial Calculations
      │
      ├── Risk Assessment
      │
      └── Final Decision
```

Example logical document structure:

```json
{
  "applicant_id": "P002",

  "comparison": {
    "identity_match": true,
    "income_match": false,
    "liability_match": false
  },

  "calculations": {
    "verified_monthly_net": 55000,
    "declared_emi": 5000,
    "detected_emi": 15000,
    "dti_ratio_percent": 27.27
  },

  "risk_assessment": {
    "risk_level": "MEDIUM",
    "anomalies": [
      "INCOME_MISMATCH",
      "UNDISCLOSED_LIABILITY"
    ]
  },

  "recommendation": "REVIEW"
}
```

---

# 📁 Project Structure

A suggested project structure is:

```text
Loan-Processing-with-GenAI/
│
├── comparison_engine/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── comparison.py
│   ├── schemas.py
│   └── ...
│
├── step5_calculation/
│   ├── __init__.py
│   ├── income.py
│   ├── obligations.py
│   ├── statement.py
│   └── eligibility.py
│
├── decision_engine/
│   ├── __init__.py
│   ├── pipeline.py
│   └── schemas.py
│
├── step6_risk/
│   ├── __init__.py
│   ├── risk.py
│   ├── anomaly.py
│   └── policy.py
│
├── database/
│   ├── __init__.py
│   ├── db_config.py
│   └── crud.py
│
├── scripts/
│   ├── process_all.py
│   └── test_mongodb.py
│
├── extracted_data/
│   └── *.json
│
├── policies/
│   └── policy.yaml
│
├── .env
├── requirements.txt
└── README.md
```

> The exact file names may vary depending on the current implementation.

---

# ⚙️ Technologies Used

| Technology          | Purpose                         |
| ------------------- | ------------------------------- |
| Python              | Core development                |
| Generative AI / LLM | Semantic analysis and reasoning |
| OCR / VLM           | Document information extraction |
| Pydantic            | Structured data validation      |
| MongoDB Atlas       | Data storage                    |
| PyMongo             | MongoDB connectivity            |
| YAML                | Policy configuration            |
| FastAPI             | API layer, if enabled           |
| Git / GitHub        | Version control                 |

---

# 🔧 Installation

## 1. Clone the repository

```bash
git clone <repository-url>
cd Loan-Processing-with-GenAI
```

## 2. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file in the project root.

Example:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-url>/
MONGODB_DATABASE=loan_processing

GROQ_API_KEY=<your-api-key>
```

Never commit the `.env` file to GitHub.

Add:

```text
.env
venv/
__pycache__/
*.pyc
```

to `.gitignore`.

---

# ▶️ Running the Pipeline

To process all applications available in MongoDB:

```bash
python -m scripts.process_all
```

Expected output:

```text
Found 10 applications.

Processing P001...
Processing P002...
Processing P003...
...

==============================
PROCESSING COMPLETE
==============================

Successful: 10
Failed: 0
```

---

# 🔎 MongoDB Connection Testing

Before running the complete pipeline, MongoDB connectivity can be verified.

```bash
python -m scripts.test_mongodb
```

Expected output:

```text
Connected to MongoDB
Database: loan_processing

Collections:
applications
comparison_results
risk_assessments

applications: 10
```

If the script reports:

```text
Found 0 applications.
```

check:

1. MongoDB URI
2. Database name
3. Collection name
4. MongoDB Atlas network access
5. Whether documents actually exist
6. Query/filter used by `process_all.py`

---

# 📤 Output

For every applicant, the system produces a structured final decision.

Example:

```json
{
  "applicant_id": "P002",
  "final_risk_score": 72,
  "final_risk_level": "HIGH",
  "recommendation": "REVIEW",
  "audit_notes": "Income mismatch and undisclosed liability detected."
}
```

---

# 🧪 Testing

The project can be tested at multiple levels.

### Unit Testing

Test individual functions:

```text
calculate_income()
calculate_obligations()
calculate_statement_metrics()
calculate_eligibility()
```

### Integration Testing

Test:

```text
MongoDB
   ↓
Comparison Engine
   ↓
Step 5
   ↓
Step 6
   ↓
Decision Engine
```

### Batch Testing

Process multiple applicants:

```bash
python -m scripts.process_all
```

Verify:

```text
Total applications
Successful applications
Failed applications
Final decisions
```

---

# 🛡️ Explainability and Auditability

The system maintains information explaining why a loan application received a particular risk classification.

Example:

```text
Risk Level: HIGH

Reasons:
- Declared income is higher than verified income.
- Bank statement indicates an undisclosed EMI.
- DTI exceeds configured threshold.

Recommendation:
REVIEW
```

This makes the system more suitable for human-in-the-loop loan processing.

---

# 👤 Human-in-the-Loop

The system is designed as a **decision-support system**, rather than blindly replacing human loan officers.

```text
                 AI Processing
                      │
                      ▼
               Risk Assessment
                      │
             ┌────────┴────────┐
             │                 │
          LOW RISK         HIGH RISK
             │                 │
             ▼                 ▼
        Auto/Quick          Human Review
          Review
```

High-risk or anomalous applications can be sent for manual verification.

---

# 🚀 Future Enhancements

Potential future improvements include:

* Real-time document upload
* FastAPI-based REST API
* Web dashboard
* Automated document classification
* Advanced VLM-based extraction
* Fraud pattern detection
* Explainable risk scoring
* Configurable policy engine
* Human review dashboard
* Application-level audit trail
* Confidence scoring
* Historical applicant analysis
* Model monitoring
* Automated report generation
* Role-based access control
* Encryption and stronger data security

---

# 🔮 Future Architecture

```text
                   ┌──────────────────┐
                   │   User / Bank    │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │   FastAPI API    │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Document Parser  │
                   │ OCR + VLM + LLM  │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │    MongoDB       │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Comparison Engine│
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Step 5           │
                   │ Calculations      │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Step 6           │
                   │ Risk + Anomaly   │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Decision Engine  │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Final Decision   │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │ Human Reviewer   │
                   └──────────────────┘
```

---

# 📌 Key Design Principles

### 1. Separation of Responsibilities

Each module has a specific responsibility:

```text
Extraction
    ↓
Comparison
    ↓
Calculation
    ↓
Risk Assessment
    ↓
Decision
```

### 2. Deterministic Financial Calculations

Financial calculations should be performed using deterministic Python logic rather than relying on LLM-generated arithmetic.

### 3. Structured Outputs

Pydantic models are used where structured validation is required.

### 4. Explainability

Every important decision should have identifiable reasons and audit notes.

### 5. Modular Architecture

Each engine can be independently tested and modified.

### 6. Human Oversight

High-risk decisions should be reviewable by a human underwriter.

---

# 📈 Example End-to-End Flow

For applicant `P002`:

```text
1. Application received
        ↓
2. Documents extracted
        ↓
3. Data stored in MongoDB
        ↓
4. Comparison Engine runs
        ↓
5. Income mismatch detected
        ↓
6. Undisclosed EMI detected
        ↓
7. Verified income calculated
        ↓
8. DTI calculated
        ↓
9. Eligibility rules evaluated
        ↓
10. Risk score calculated
        ↓
11. Risk classified as HIGH
        ↓
12. Recommendation generated
        ↓
13. Final decision stored in MongoDB
```

---

# 👥 Project Contribution

The project consists of multiple modules developed collaboratively.

The **Declared vs Verified Document Comparison Engine** focuses on:

* Receiving extracted document data
* Comparing declared and verified information
* Identifying inconsistencies
* Calculating verified financial values
* Detecting undisclosed liabilities
* Producing structured `ComparisonResult`
* Passing verified results to the Decision Engine

---

# 📄 License

This project is developed for educational, research, and demonstration purposes.

---

# ⭐ Summary

The Loan Processing using Generative AI system combines:

**Generative AI + Document Intelligence + Deterministic Financial Calculations + Rule-Based Policies + Risk Analysis + MongoDB**

to create an automated and explainable loan-processing pipeline.

The core principle is:

```text
Extract → Compare → Calculate → Assess Risk → Decide → Explain
```
