from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator


class Campaign(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(default='Campaign', max_length=80)
    location: str = Field(default='', max_length=160)
    summary: str = Field(default='', max_length=240)
    currency: str = Field(default='NGN', pattern=r'^[A-Z]{3}$')
    goal: float | None = Field(default=None, ge=0)
    raised: float | None = Field(default=None, ge=0)
    public_progress: bool = False


class ConversationMessage(BaseModel):
    role: Literal['user','assistant']
    content: str = Field(min_length=1,max_length=650)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=600)
    history: list[ConversationMessage] = Field(default_factory=list, max_length=8)
    campaigns: list[Campaign] = Field(default_factory=list,max_length=30)

    @field_validator('message')
    @classmethod
    def nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class SuggestedAllocation(BaseModel):
    id: int = Field(gt=0)
    amount: int = Field(gt=0)


class SuggestedPlan(BaseModel):
    currency: str
    budget: int = Field(gt=0)
    items: list[SuggestedAllocation] = Field(min_length=1,max_length=10)


class ChatResponse(BaseModel):
    reply: str = Field(max_length=3000)
    campaign_ids: list[int] = Field(default_factory=list)
    plan_proposal: SuggestedPlan | None = None
    agents_run: list[str] = Field(default_factory=list)
    mode: str = 'langgraph'
