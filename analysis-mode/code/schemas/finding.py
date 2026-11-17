"""Finding contract, compatible with Pydantic 1 and 2."""
import math

try:
    from pydantic.v1 import BaseModel, Field, StrictStr, validator
except ImportError:
    from pydantic import BaseModel, Field, StrictStr, validator


class Finding(BaseModel):
    location: StrictStr
    kind: StrictStr
    evidence: StrictStr
    confidence: float = Field(..., ge=0, le=1)

    @validator("location", "kind", "evidence")
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("must be a nonempty string")
        return value

    @validator("confidence", pre=True)
    def numeric_confidence(cls, value):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not 0 <= value <= 1 or not math.isfinite(value)):
            raise ValueError("must be a finite number between 0 and 1")
        return value

    class Config:
        extra = "forbid"
