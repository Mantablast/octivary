import os
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from .models import SavedSearch, SavedSearchCreate

# In-memory storage for scaffolding only.
_saved_searches: Dict[str, SavedSearch] = {}

_DYNAMO_AVAILABLE = False
_saved_searches_table = None

try:
    import boto3  # type: ignore

    _DYNAMO_AVAILABLE = True
except Exception:
    _DYNAMO_AVAILABLE = False


def _load_saved_searches_table() -> Optional[object]:
    table_name = os.getenv("SAVED_SEARCHES_TABLE")
    if not table_name or not _DYNAMO_AVAILABLE:
        return None
    try:
        resource = boto3.resource("dynamodb")
        return resource.Table(table_name)
    except Exception:
        return None


_saved_searches_table = _load_saved_searches_table()


def list_saved_searches(user_id: str) -> List[SavedSearch]:
    if _saved_searches_table:
        from boto3.dynamodb.conditions import Key  # type: ignore

        response = _saved_searches_table.query(
            IndexName="UserIdIndex",
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        items = response.get("Items", [])
        return [SavedSearch(**item) for item in items]
    return [search for search in _saved_searches.values() if search.user_id == user_id]


def get_saved_search(search_id: str) -> SavedSearch | None:
    if _saved_searches_table:
        response = _saved_searches_table.get_item(Key={"search_id": search_id})
        item = response.get("Item")
        return SavedSearch(**item) if item else None
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
    if _saved_searches_table:
        item = search.model_dump()
        item["created_at"] = search.created_at.isoformat()
        item["updated_at"] = search.updated_at.isoformat()
        _saved_searches_table.put_item(Item=item)
    else:
        _saved_searches[search.search_id] = search
    return search


def delete_saved_search(search_id: str) -> bool:
    if _saved_searches_table:
        _saved_searches_table.delete_item(Key={"search_id": search_id})
        return True
    return _saved_searches.pop(search_id, None) is not None
