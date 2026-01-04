from datetime import datetime
from typing import Any, Dict, Optional
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
