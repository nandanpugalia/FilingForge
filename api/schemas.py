"""HTTP request/response models. Mirrors the engine's vocabulary; `kinds` are the string
names the UI sends, validated against the engine's FilingType enum."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from engine.models import FilingType

_VALID_KINDS = [t.name.lower() for t in FilingType]   # annual_report, results, investor_ppt, concall
_DEFAULT_KINDS = list(_VALID_KINDS)


class ResolveRequest(BaseModel):
    company: str = Field(min_length=1)


class CandidateOut(BaseModel):
    scrip_code: str
    company: str
    is_primary: bool


class BuildRequest(BaseModel):
    scrip_code: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    dest: str = Field(min_length=1)
    years: int = Field(default=5, ge=1, le=25)
    kinds: list[str] = Field(default_factory=lambda: list(_DEFAULT_KINDS))

    @field_validator("kinds")
    @classmethod
    def _validate_kinds(cls, v: list[str]) -> list[str]:
        bad = [k for k in v if k not in _VALID_KINDS]
        if bad:
            raise ValueError(f"unknown filing kinds: {bad}; valid = {_VALID_KINDS}")
        return v


class JobCreated(BaseModel):
    job_id: str


class JobStatusOut(BaseModel):
    job_id: str
    status: str                              # queued | running | done | error
    progress: Optional[dict] = None          # last ProgressEvent as a dict
    result: Optional[dict] = None            # {downloaded, skipped, failed} counts when done
    error: Optional[str] = None              # friendly user_message when status == error


class OpenFolderRequest(BaseModel):
    path: str = Field(min_length=1)
