from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# Schema dasar Lead
class LeadBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


# Schema untuk PATCH /leads/{id} (Update parsial)
class LeadUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


# Schema Response detail Lead
class LeadResponse(LeadBase):
    id: int
    source_channel: Optional[str] = None
    source_detail: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Schema untuk payload POST /leads/ingest (Format website_form_submissions.json)
class FormSubmissionIngest(BaseModel):
    form_id: Optional[str] = None
    form_name: Optional[str] = None
    page_url: Optional[str] = None
    submitted_at: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    country: Optional[str] = None
    message: Optional[str] = None


# Schema Response untuk Dedup Candidate Pair
class DedupeCandidate(BaseModel):
    candidate_pair: list[int]
    confidence_score: float
    reason: str
    leads: list[LeadResponse]