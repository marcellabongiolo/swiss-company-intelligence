from __future__ import annotations

from typing import Annotated

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from .analyzer import CompanyAnalyzer
from .models import SWISS_CANTONS
from .scoring import score_row

app = FastAPI(
    title="Swiss Company Intelligence API",
    version="0.1.0",
    description="REST API for explainable Swiss-company screening.",
)


class CompanyInput(BaseModel):
    company: str = Field(min_length=1)
    canton: str
    sector: str = Field(min_length=1)
    revenue_m_chf: Annotated[float, Field(ge=0)]
    revenue_growth_pct: float
    ebitda_margin_pct: float
    debt_to_equity: float
    current_ratio: float
    employee_growth_pct: float
    customer_concentration_pct: Annotated[float, Field(ge=0, le=100)]
    late_payment_pct: Annotated[float, Field(ge=0, le=100)]

    @field_validator("canton")
    @classmethod
    def validate_canton(cls, value: str) -> str:
        canton = value.strip().upper()
        if canton not in SWISS_CANTONS:
            raise ValueError(f"Unknown Swiss canton: {canton}")
        return canton


class ScoreRequest(BaseModel):
    debt_to_equity: float
    current_ratio: float
    customer_concentration_pct: Annotated[float, Field(ge=0, le=100)]
    late_payment_pct: Annotated[float, Field(ge=0, le=100)]
    revenue_growth_pct: float
    employee_growth_pct: float
    sector_anomaly_strength: Annotated[float, Field(ge=0, le=1)] = 0.0


class ScoreResponse(BaseModel):
    attention_score: float
    reasons: list[str]


class PortfolioRequest(BaseModel):
    companies: Annotated[list[CompanyInput], Field(min_length=1)]


class PortfolioResult(BaseModel):
    company: str
    canton: str
    sector: str
    attention_score: float
    priority_band: str
    sector_rank: int
    reasons: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score_company(request: ScoreRequest) -> ScoreResponse:
    row = pd.Series(request.model_dump())
    score, reasons = score_row(row)
    return ScoreResponse(attention_score=score, reasons=reasons)


@app.post("/analyze", response_model=list[PortfolioResult])
def analyze_portfolio(request: PortfolioRequest) -> list[PortfolioResult]:
    frame = pd.DataFrame([company.model_dump() for company in request.companies])
    analyzed = CompanyAnalyzer().analyze(frame)

    return [
        PortfolioResult(
            company=str(row.company),
            canton=str(row.canton),
            sector=str(row.sector),
            attention_score=float(row.attention_score),
            priority_band=str(row.priority_band),
            sector_rank=int(row.sector_rank),
            reasons=str(row.reasons),
        )
        for row in analyzed.itertuples(index=False)
    ]
