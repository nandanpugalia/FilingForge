"""HTTP request/response models. Mirrors the engine's vocabulary; `categories` are the
curated category keys the UI sends, validated against the engine's CURATED_BY_KEY map."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from engine.models import CURATED_BY_KEY

_VALID_KEYS = set(CURATED_BY_KEY)


class ResolveRequest(BaseModel):
    company: str = Field(min_length=1)


class CandidateOut(BaseModel):
    scrip_code: str
    company: str
    is_primary: bool
    isin: Optional[str] = None
    symbol: Optional[str] = None


class BuildRequest(BaseModel):
    scrip_code: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    dest: str = Field(min_length=1)
    years: int = Field(default=1, ge=1, le=25)
    everything: bool = True
    categories: list[str] = Field(default_factory=list)

    @field_validator("categories")
    @classmethod
    def _valid_keys(cls, v: list[str]) -> list[str]:
        bad = [k for k in v if k not in _VALID_KEYS]
        if bad:
            raise ValueError(f"unknown category keys: {bad}; valid = {sorted(_VALID_KEYS)}")
        return v


class LibraryItem(BaseModel):
    ticker: str
    total: int
    counts: dict[str, int]


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


class ImportSkillRequest(BaseModel):
    path: str = Field(min_length=1)          # absolute path to the .md the user picked


class InstallSkillRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)   # display name → slug; cap keeps the filename under NAME_MAX (422 not 500)
    content: str = Field(min_length=1)       # the .md text (e.g. a paid pack from the Worker)
