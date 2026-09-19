from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AssistantRequest(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=2000)
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    activity_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_message(self) -> "AssistantRequest":
        if not self.question and not self.message:
            raise ValueError("question or message is required")
        if self.question is None:
            self.question = self.message
        return self


class AssistantSource(BaseModel):
    type: str
    id: int


class AssistantResponse(BaseModel):
    question: str
    answer: str
    intent: str
    sources: list[AssistantSource]
    confidence: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_DATA"] = "SUPPORTED"


class AssistantProviderResult(BaseModel):
    answer: str = Field(min_length=1)
    source_ids: list[int] = Field(default_factory=list)
    confidence: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_DATA"] = "SUPPORTED"


class AssistantContext(BaseModel):
    project_id: int
    intent: str
    question: str
    records: list[dict[str, Any]]
    sources: list[AssistantSource]
