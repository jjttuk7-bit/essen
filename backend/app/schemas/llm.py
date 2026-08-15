from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(min_length=1)]
    text: Annotated[str, Field(min_length=1)]

    @field_validator("id", "text")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[SourceSegment] = Field(min_length=1)
    prompt_version: str = "semantic_extraction_v1"
