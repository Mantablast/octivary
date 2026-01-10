from datetime import datetime
from typing import Any, Dict, List, Optional
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
