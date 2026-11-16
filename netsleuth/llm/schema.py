from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Hypothesis(BaseModel):
    cause: str = Field(..., description="Root cause hypothesis explaining the failure")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence_ids: List[str] = Field(..., description="List of evidence IDs cited from the incident")
    next_test: str = Field(..., description="Recommended diagnostic test or verification step")

class ProposedFix(BaseModel):
    description: str = Field(..., description="Clear explanation of the proposed remediation")
    device: str = Field(..., description="Target network device hostname")
    commands: List[str] = Field(..., description="Exact eAPI CLI configuration commands to apply")
    risk: str = Field(..., description="Risk assessment: low, medium, high, none")
    rollback: List[str] = Field(default_factory=list, description="Commands to revert changes if verification fails")

class LLMDiagnosis(BaseModel):
    summary: str = Field(..., description="High-level executive summary of the incident")
    hypotheses: List[Hypothesis] = Field(..., description="Ranked list of root cause hypotheses")
    proposed_fix: ProposedFix = Field(..., description="Concrete, deterministic proposed remediation")
