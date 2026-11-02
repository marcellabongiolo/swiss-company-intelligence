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
    revenue_m_chf: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    revenue_growth_pct: Annotated[float, Field(allow_inf_nan=False)]
    ebitda_margin_pct: Annotated[float, Field(allow_inf_nan=False)]
    debt_to_equity: Annotated[float, Field(allow_inf_nan=False)]
    current_ratio: Annotated[float, Field(allow_inf_nan=False)]
    employee_growth_pct: Annotated[float, Field(allow_inf_nan=False)]
    customer_concentration_pct: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
    late_payment_pct: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]

    @field_validator("company", "sector")
    @classmethod
    def validate_required_label(cls, value: str) -> str:
        label = value.strip()
        if not label:
            raise ValueError("Company and sector must not be blank")
        return label

    @field_validator("canton")
    @classmethod
    def validate_canton(cls, value: str) -> str:
        canton = value.strip().upper()
        if canton not in SWISS_CANTONS:
            raise ValueError(f"Unknown Swiss canton: {canton}")
        return canton


class ScoreRequest(BaseModel):
    debt_to_equity: Annotated[float, Field(allow_inf_nan=False)]
    current_ratio: Annotated[float, Field(allow_inf_nan=False)]
    customer_concentration_pct: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
    late_payment_pct: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
    revenue_growth_pct: Annotated[float, Field(allow_inf_nan=False)]
    employee_growth_pct: Annotated[float, Field(allow_inf_nan=False)]
    sector_anomaly_strength: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = 0.0


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
