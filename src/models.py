from pydantic import BaseModel, Field
from typing import Literal


class SentimentResult(BaseModel):
    """The structured shape you'll force the model to return.
    TODO define fields:
      sentiment: Literal["positive","neutral","negative"]
      confidence: float   # Field(ge=0, le=1)
      key_issues: list[str]   # concrete problems the customer named
      summary: str
    """
    sentiment: Literal["positive","neutral","negative"]
    confidence: float = Field(ge=0, le=1)
    key_issues: list[str]
    summary: str


class ReviewAnalysis(BaseModel):
    """Richer schema than SentimentResult - Day 2's LCEL chain returns this.
    TODO fields: sentiment, confidence, summary, themes: list[str],
       severity: int (Field ge=1 le=5), suggested_category: str
    """
    sentiment: Literal["positive","neutral","negative"]
    confidence: float  = Field(ge=0, le=1)
    summary: str
    themes: list[str]
    severity: int = Field(ge=1, le=5)
    suggested_category : str
