from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SavedSearchCreate(BaseModel):
    category_key: str
    config_key: str
    priority_payload: Dict[str, Any] = Field(default_factory=dict)
    filters_payload: Dict[str, Any] = Field(default_factory=dict)


class SavedSearch(SavedSearchCreate):
    search_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class ItemsRequest(BaseModel):
    config_key: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    priorities: Dict[str, Any] = Field(default_factory=dict)


class ItemResult(BaseModel):
    item_id: str
    title: str
    score: float
    price: Optional[float] = None


class ReverbListingsRequest(BaseModel):
    config_key: Optional[str] = None
    query: Optional[str] = None
    category_uuid: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    page: int = 1
    per_page: int = 24


class ListingsSearchRequest(BaseModel):
    config_key: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    selected_order: Dict[str, List[str]] = Field(default_factory=dict)
    section_order: List[str] = Field(default_factory=list)
    page: int = 1
    per_page: int = 24


class DynamicSearchJobCreate(BaseModel):
    query: str
    limit: int = 12


class DynamicSearchFilterOption(BaseModel):
    label: str
    value: str
    count: int | None = None


class DynamicSearchFilterSummary(BaseModel):
    key: str
    label: str
    type: str
    option_count: int | None = None
    options: List[DynamicSearchFilterOption] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None
    path: str | None = None
    helper_text: str | None = None


class DynamicSearchListingMetadata(BaseModel):
    label: str
    value: str


class DynamicSearchListingSummary(BaseModel):
    listing_id: str
    title: str
    subtitle: str | None = None
    score: float
    image_url: str | None = None
    metadata: List[DynamicSearchListingMetadata] = Field(default_factory=list)
    source_url: str | None = None


class DynamicSearchCandidate(BaseModel):
    config_key: str
    title: str
    category_key: str
    description: str
    match_score: float
    evidence_count: int
    source_type: str
    local_data_available: bool = True


class DynamicSearchResult(BaseModel):
    query: str
    config_key: str | None = None
    config_title: str | None = None
    config_description: str | None = None
    category_key: str | None = None
    evidence_count: int = 0
    prefill_filters: Dict[str, Any] = Field(default_factory=dict)
    prefill_selected_order: Dict[str, List[str]] = Field(default_factory=dict)
    prefill_section_order: List[str] = Field(default_factory=list)
    generated_config: Dict[str, Any] | None = None
    generated_listings: List[Dict[str, Any]] = Field(default_factory=list)
    generated_filters: List[DynamicSearchFilterSummary] = Field(default_factory=list)
    listings: List[DynamicSearchListingSummary] = Field(default_factory=list)
    candidates: List[DynamicSearchCandidate] = Field(default_factory=list)
    local_only: bool = True
    note: str | None = None
    open_filter_path: str | None = None


class DynamicSearchJob(BaseModel):
    job_id: str
    user_id: str
    query: str
    limit: int = 12
    status: Literal["queued", "running", "completed", "failed"]
    progress: float = 0.0
    current_step: str
    profile: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
    result: DynamicSearchResult | None = None


class DynamicJobScoreRequest(BaseModel):
    filters: Dict[str, Any] = Field(default_factory=dict)
    selected_order: Dict[str, List[str]] = Field(default_factory=dict)
    section_order: List[str] = Field(default_factory=list)
    page: int = 1
    per_page: int = 24
