from pydantic import BaseModel, Field
from typing import Literal, Optional

# ---------------------------------------------------------
# Relevance Evaluator (Module 6) Output
# ---------------------------------------------------------
class RelevanceOutput(BaseModel):
    is_relevant: bool = Field(description="True if this is a factual financial disclosure or event, False if it is a rumor, opinion piece, or unrelated news.")
    legal_pass: bool = Field(description="True if it passes legal safety checks (not insider info, not investment advice).")
    algorithmic_pass: bool = Field(description="True if it mentions specific companies or macroeconomic data.")
    relevance_outcome: Literal["RELEVANT", "NOT_RELEVANT"]

# ---------------------------------------------------------
# Generation Engine (Module 7) Output
# ---------------------------------------------------------
class GenerationOutput(BaseModel):
    summary_5_sec: str = Field(
        description="A bold, highly scannable headline summarizing the most critical impact of the event.",
        max_length=150
    )
    breakdown_30_sec: str = Field(
        description="A descriptive paragraph explaining the core details, financial metrics, and immediate market context.",
        max_length=500
    )
    ticker: str = Field(
        description="The uppercase stock symbol/ticker of the main company mentioned, or 'GENERAL'."
    )
    sector: str = Field(
        description="The industry sector of the company (e.g., Energy, IT, Financial Services, Automobile, Consumer Goods, Telecom) or 'Macro'."
    )
    
# ---------------------------------------------------------
# Safety & Confidence Validator (Module 9) Output
# ---------------------------------------------------------
class ValidationOutput(BaseModel):
    confidence_score: int = Field(
        description="A score from 0 to 100 representing the certainty that the generated summary is factually accurate and purely descriptive.",
        ge=0,
        le=100
    )
    safety_status: Literal["PASS", "FAIL"] = Field(
        description="PASS if the summary contains no financial advice. FAIL if it predicts future prices or tells users what to buy/sell."
    )
    status: Literal["APPROVED", "LOW_CONFIDENCE", "REJECTED"] = Field(
        description="APPROVED if confidence >= 85 and safety == PASS. LOW_CONFIDENCE if confidence < 85. REJECTED if safety == FAIL."
    )

# ---------------------------------------------------------
# Combined API Response Schema (Internal Java -> Python API)
# ---------------------------------------------------------
class AIAnalysisResponse(BaseModel):
    transaction_id: str
    relevance_outcome: Literal["RELEVANT", "NOT_RELEVANT"]
    relevance_metrics: RelevanceOutput
    ai_analysis: Optional[GenerationOutput] = None
    metrics: Optional[ValidationOutput] = None

# ---------------------------------------------------------
# On-Demand Discovery Output
# ---------------------------------------------------------
class DiscoveryOutput(BaseModel):
    relevance_outcome: Literal["RELEVANT", "NOT_RELEVANT"]
    headline: Optional[str] = Field(description="A clean, factual headline of the main event if found.", default=None)
    summary_5_sec: Optional[str] = Field(description="A bold, highly scannable headline summarizing the most critical impact.", default=None)
    breakdown_30_sec: Optional[str] = Field(description="A descriptive paragraph explaining the core details and metrics.", default=None)
    ticker: Optional[str] = Field(description="The uppercase stock symbol/ticker of the main company (e.g. RELIANCE), or 'GENERAL'.", default=None)
    sector: Optional[str] = Field(description="The industry sector of the company (e.g. Energy, IT, Financial Services) or 'Macro'.", default=None)
    source_url: Optional[str] = Field(description="The original source URL (from the provided search results) of the main article summarized.", default=None)
