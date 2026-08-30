from pydantic import BaseModel, Field
from typing import Optional

# IMPORTANT: Update the schema as per our data.

class PANCardExtract(BaseModel):
    full_name: str = Field(description="Full legal name of cardholder")
    pan_number: str = Field(description="10-digit alphanumeric PAN number")
    dob: str = Field(description="Date of birth in DD/MM/YYYY or YYYY-MM-DD")
    fathers_name: Optional[str] = Field(default=None, description="Father's name if present")

class IDProofExtract(BaseModel):
    full_name: str = Field(description="Full legal name of the applicant")
    id_type: str = Field(description="Passport, Voter ID, Driving License, or Aadhaar")
    address: Optional[str] = Field(default=None, description="Residential address listed")
    dob: Optional[str] = Field(default=None, description="Date of birth")