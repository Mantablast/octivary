from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from .models import SavedSearch, SavedSearchCreate

# In-memory storage for scaffolding only.
_saved_searches: Dict[str, SavedSearch] = {}


def list_saved_searches(user_id: str) -> List[SavedSearch]:
    return [search for search in _saved_searches.values() if search.user_id == user_id]


def get_saved_search(search_id: str) -> SavedSearch | None:
    return _saved_searches.get(search_id)


def create_saved_search(user_id: str, payload: SavedSearchCreate) -> SavedSearch:
    now = datetime.utcnow()
    search = SavedSearch(
        search_id=str(uuid4()),
        user_id=user_id,
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    )
    _saved_searches[search.search_id] = search
    return search


def delete_saved_search(search_id: str) -> bool:
    return _saved_searches.pop(search_id, None) is not None
