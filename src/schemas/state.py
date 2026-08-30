from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from src.schemas.kyc_schemas import PANCardExtract, IDProofExtract
from src.schemas.income_schemas import SalarySlipExtract, Form16ITRExtract

# This need to be fixed by me(Shashank), it will be done after all the schema is updated.

class LoanProcessingState(BaseModel):
    application_id: str
    raw_files: List[Dict[str, Any]] = Field(default_factory=list) # [{"filename": "...", "bytes": ...}]
    
    # Classifications
    doc_types: Dict[str, str] = Field(default_factory=dict) # {"file1.pdf": "PAN_CARD"}
    
    # Extracted Records
    extracted_kyc: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_salary_slips: List[SalarySlipExtract] = Field(default_factory=list)
    extracted_tax_forms: List[Form16ITRExtract] = Field(default_factory=list)
    
    # Financial Computations
    verified_monthly_income: Optional[float] = None
    calculated_dti: Optional[float] = None
    discrepancies: List[str] = Field(default_factory=list)
    
    # Underwriting Verdict
    underwriting_status: Literal["APPROVED", "REJECTED", "MANUAL_REVIEW"] = "MANUAL_REVIEW"
    decision_summary: Optional[str] = None