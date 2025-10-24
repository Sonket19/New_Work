"""Pydantic models representing the Deal document stored in Firestore."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FounderProfile(BaseModel):
    """Details about the founding team."""

    name: str
    education: Optional[str] = None
    professional_background: Optional[str] = Field(default=None, alias="professional_background")
    previous_ventures: Optional[str] = None

    class Config:
        populate_by_name = True


class MarketSizeMetric(BaseModel):
    name: str
    value: Optional[str] = None
    cagr: Optional[str] = None
    source: Optional[str] = None
    projection: Optional[str] = None


class CompetitorDetail(BaseModel):
    name: str
    category: Optional[str] = None
    business_model: Optional[str] = None
    funding: Optional[str] = None
    margins: Optional[str] = None
    commentary: Optional[str] = None


class ClaimAnalysis(BaseModel):
    claim: str
    analysis_method: Optional[str] = None
    input_dataset_length: Optional[str] = None
    simulation_assumptions: Optional[str] = None
    simulated_probability: Optional[str] = None
    result: Optional[str] = None


class FinancialProjection(BaseModel):
    year: str
    revenue: str


class MemoMarketAnalysis(BaseModel):
    industry_size_and_growth: Optional[dict] = None
    sub_segment_opportunities: List[str] = Field(default_factory=list)
    competitor_details: List[CompetitorDetail] = Field(default_factory=list)
    recent_news: Optional[str] = None


class MemoBusinessModel(BaseModel):
    revenue_streams: Optional[str] = None
    pricing: Optional[str] = None
    unit_economics: Optional[str] = None
    scalability: Optional[str] = None


class MemoFinancials(BaseModel):
    arr_mrr: Optional[dict] = None
    burn_and_runway: Optional[dict] = None
    funding_history: Optional[str] = None
    valuation_rationale: Optional[str] = None
    projections: List[FinancialProjection] = Field(default_factory=list)


class MemoRiskMetrics(BaseModel):
    composite_risk_score: Optional[float] = None
    score_interpretation: Optional[str] = None
    narrative_justification: Optional[str] = None


class MemoConclusion(BaseModel):
    overall_attractiveness: Optional[str] = None


class MemoCompanyOverview(BaseModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    founders: List[FounderProfile] = Field(default_factory=list)
    technology: Optional[str] = None


class MemoDraft(BaseModel):
    company_overview: MemoCompanyOverview
    market_analysis: MemoMarketAnalysis
    business_model: MemoBusinessModel
    financials: MemoFinancials
    claims_analysis: List[ClaimAnalysis]
    risk_metrics: MemoRiskMetrics
    conclusion: MemoConclusion


class MemoDocument(BaseModel):
    draft_v1: MemoDraft
    generated_at: datetime
    docx_url: Optional[str] = None


class DealWeightage(BaseModel):
    traction: int = 20
    team_strength: int = 20
    claim_credibility: int = 20
    financial_health: int = 20
    market_opportunity: int = 20


class DealMetadata(BaseModel):
    weightage: DealWeightage
    created_at: datetime
    status: str
    deal_id: str
    company_name: Optional[str] = None
    processed_at: Optional[datetime] = None
    error: Optional[str] = None
    sector: Optional[str] = None
    founder_names: List[str] = Field(default_factory=list)


class RawFiles(BaseModel):
    pitch_deck_url: Optional[str] = None


class MemoRegenerationRequest(DealWeightage):
    """Incoming payload for memo regeneration requests."""


class UploadResponse(BaseModel):
    deal_id: str
    status: str


class OperationResponse(BaseModel):
    message: str


class FounderChatTranscript(BaseModel):
    participant: str
    message: str
    timestamp: datetime


class FounderInvite(BaseModel):
    token: str
    founder_email: str
    expires_at: datetime
    used: bool = False
    invite_url: Optional[str] = None


class FounderInviteRequest(BaseModel):
    founder_email: str
    expires_in_minutes: int = Field(default=60, ge=5, le=1440)


class FounderInviteResponse(BaseModel):
    invite_url: str
    expires_at: datetime


class DealDocument(BaseModel):
    raw_files: RawFiles
    public_data: dict
    metadata: DealMetadata
    extracted_text: dict
    memo: MemoDocument
    founder_chat: List[FounderChatTranscript] = Field(default_factory=list)
    founder_invite: Optional[FounderInvite] = None

