from typing import Literal

from pydantic import BaseModel, Field

PROMPT = """You analyse Indian stock market news for ONE company: {ticker} ({names}).
Headline: {headline}

relevant: true only if the headline reports a concrete event that could move this company's share price
(results, orders, deals, regulatory action, management change, guidance). False for listicles,
market wrap-ups, opinion, jobs/exam news, or items about a different entity with a similar name.
direction: likely short-term price reaction implied by the facts in the headline. Use "neutral" if unclear.
confidence: 0-1, how clearly the headline alone supports that direction.
summary: at most 2 sentences using only facts stated in the headline. Do not invent numbers."""


class SignalOutput(BaseModel):
    relevant: bool
    direction: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(max_length=400)


def analyze(ticker: str, names: list[str], headline: str) -> SignalOutput | None:
    """Reuses the engine's Gemini client rotation. Returns None if the item is not relevant."""
    from src.pipelines.ai_engine import generate_content  # imported lazily: needs GEMINI_API_KEYS
    resp = generate_content(PROMPT.format(ticker=ticker, names=", ".join(names), headline=headline),
                            SignalOutput, temperature=0.0)
    out = SignalOutput.model_validate_json(resp.text)
    return out if out.relevant else None
