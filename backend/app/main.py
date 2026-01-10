import hashlib
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import requests

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

from .auth import require_user
from .cache import response_cache
from .config_loader import list_config_keys, load_filter_config
from .cost_guardrail import guard_if_paused
from .listings_store import load_local_listings
from .mcda_scoring import score_listings
from .models import (
    ItemsRequest,
    ItemResult,
    ListingsSearchRequest,
    SavedSearchCreate,
    ReverbListingsRequest,
)
from .provider_registry import resolve_provider
from .rate_limit import enforce_rate_limit
from .storage import (
    create_saved_search,
    delete_saved_search,
    get_saved_search,
    list_saved_searches,
)

app = FastAPI(title='Octivary API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in os.getenv('CORS_ALLOW_ORIGINS', '*').split(',') if origin],
    allow_methods=['*'],
    allow_headers=['*'],
)


def _user_id_from_request(request: Request) -> str:
    return getattr(request.state, 'user_id', None) or request.headers.get('x-user-id', 'demo-user')


@app.on_event('startup')
async def validate_provider_configs() -> None:
    if os.getenv('VALIDATE_PROVIDER_KEYS') != '1':
        return
    for config_key in list_config_keys():
        config = load_filter_config(config_key)
        provider_key = config['datasets']['primary']['data_source']['provider_key']
        resolve_provider(provider_key)


@app.get('/api/health')
async def health() -> dict:
    return {'status': 'ok'}


@app.get('/api/config/{config_key}')
async def get_config(config_key: str) -> dict:
    try:
        return load_filter_config(config_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r'[^a-z0-9]+', '-', normalized)
    return normalized.strip('-')


def _coerce_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if item is not None and str(item).strip() != '']
    return [str(value).strip()]


def _extract_range(value: object) -> tuple[float | None, float | None]:
    if not isinstance(value, dict):
        return None, None
    min_value = value.get('min')
    max_value = value.get('max')
    try:
        min_parsed = float(min_value) if min_value is not None else None
    except (TypeError, ValueError):
        min_parsed = None
    try:
        max_parsed = float(max_value) if max_value is not None else None
    except (TypeError, ValueError):
        max_parsed = None
    return min_parsed, max_parsed


def _merge_query(base: str | None, extras: list[str]) -> str | None:
    parts = [base.strip()] if base else []
    for term in extras:
        cleaned = term.strip()
        if cleaned:
            parts.append(cleaned)
    if not parts:
        return None
    return ' '.join(parts)


def _build_reverb_params(
    config_key: str | None,
    query: str | None,
    category_uuid: str | None,
    page: int,
    per_page: int,
    filters: dict,
) -> dict:
    params: dict[str, str | int | list[str]] = {}
    preset_query = None

    if config_key:
        config = load_filter_config(config_key)
        preset = config.get('preset_filters', {})
        preset_query = preset.get('query')
        for key, value in preset.items():
            if value is None or value == '':
                continue
            params[key] = value

    if category_uuid:
        params['category_uuid'] = category_uuid

    extra_terms = []
    if query:
        extra_terms.append(query)
    extra_terms.extend(_coerce_list(filters.get('description')))
    model_terms = _coerce_list(filters.get('model'))
    if len(model_terms) == 1:
        extra_terms.append(model_terms[0])
    finish_terms = _coerce_list(filters.get('finish'))
    if len(finish_terms) == 1:
        extra_terms.append(finish_terms[0])
    query_terms = _merge_query(preset_query, extra_terms)
    if query_terms:
        params['query'] = query_terms

    makes = _coerce_list(filters.get('make'))
    if makes:
        if len(makes) == 1:
            params['make'] = makes[0]
        else:
            params['make[]'] = makes

    conditions = [_slugify(entry) for entry in _coerce_list(filters.get('condition_display'))]
    if conditions:
        if len(conditions) == 1:
            params['condition'] = conditions[0]
        else:
            params['condition[]'] = conditions

    price_min, price_max = _extract_range(filters.get('price'))
    if price_min is not None:
        params['price_min'] = price_min
    if price_max is not None:
        params['price_max'] = price_max

    year_min, year_max = _extract_range(filters.get('year'))
    if year_min is not None:
        params['year_min'] = int(year_min)
    if year_max is not None:
        params['year_max'] = int(year_max)

    if filters.get('free_expedited_shipping') is True:
        params['free_expedited_shipping'] = 'true'

    per_page = max(1, min(int(per_page), 50))
    page = max(1, int(page))
    params['per_page'] = per_page
    params['page'] = page

    return params


def _fetch_reverb_listings(params: dict) -> dict:
    base_url = os.getenv('PROVIDER_REVERB_V1_BASE_URL', 'https://api.reverb.com/api')
    api_key = os.getenv('PROVIDER_REVERB_V1_API_KEY')

    headers = {
        'Accept-Version': '3.0',
    }
    if api_key:
        headers['Authorization'] = f"Bearer {api_key}"

    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/listings",
            headers=headers,
            params=params,
            timeout=12,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get('/api/reverb/listings')
async def get_reverb_listings(
    request: Request,
    _claims: dict = Depends(require_user),
    config_key: str | None = None,
    query: str | None = None,
    category_uuid: str | None = None,
    page: int = 1,
    per_page: int = 24,
) -> dict:
    enforce_rate_limit(request)
    try:
        params = _build_reverb_params(config_key, query, category_uuid, page, per_page, {})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _fetch_reverb_listings(params)


@app.post('/api/reverb/listings')
async def post_reverb_listings(
    request: Request,
    payload: ReverbListingsRequest,
    _claims: dict = Depends(require_user),
) -> dict:
    enforce_rate_limit(request)
    try:
        params = _build_reverb_params(
            payload.config_key,
            payload.query,
            payload.category_uuid,
            payload.page,
            payload.per_page,
            payload.filters,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _fetch_reverb_listings(params)


@app.post('/api/items', response_model=list[ItemResult])
async def get_items(payload: ItemsRequest) -> list[ItemResult]:
    guard_if_paused()
    try:
        config = load_filter_config(payload.config_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    provider_key = config['datasets']['primary']['data_source']['provider_key']
    resolve_provider(provider_key)
    return [
        ItemResult(item_id='item-1', title='Featured listing', score=88.0, price=420),
        ItemResult(item_id='item-2', title='Best value pick', score=80.0, price=310),
        ItemResult(item_id='item-3', title='Premium option', score=92.0, price=680),
    ]


def _payload_cache_key(payload: ListingsSearchRequest, user_id: str) -> str:
    digest = hashlib.sha256(
        json.dumps(payload.model_dump(), sort_keys=True, default=str).encode('utf-8')
    ).hexdigest()
    return f"listings:{user_id}:{digest}"


@app.post('/api/listings/search')
async def search_listings(
    payload: ListingsSearchRequest,
    request: Request,
    _claims: dict = Depends(require_user),
) -> dict:
    guard_if_paused()
    enforce_rate_limit(request)
    user_id = _user_id_from_request(request)
    cache_key = _payload_cache_key(payload, user_id)
    cached = response_cache.get(cache_key)
    if cached:
        return cached

    config = load_filter_config(payload.config_key)
    data_source = config['datasets']['primary']['data_source']
    provider_key = data_source.get('provider_key', '')
    source_type = data_source.get('type')

    if source_type == 'local_json':
        listings = load_local_listings(provider_key)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Unsupported data source for server-side scoring.',
        )

    scored, _ = score_listings(
        listings=listings,
        config=config,
        filters=payload.filters,
        selected_order=payload.selected_order,
        section_order=payload.section_order,
    )

    per_page = max(1, min(int(payload.per_page), 50))
    page = max(1, int(payload.page))
    total = len(scored)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    response = {
        'listings': scored[start : start + per_page],
        'total': total,
        'per_page': per_page,
        'current_page': page,
        'total_pages': total_pages,
    }
    response_cache.set(cache_key, response)
    return response


@app.get('/api/saved-searches')
async def get_saved_searches(request: Request, _claims: dict = Depends(require_user)) -> list[dict]:
    guard_if_paused()
    user_id = _user_id_from_request(request)
    return [search.model_dump() for search in list_saved_searches(user_id)]


@app.post('/api/saved-searches')
async def create_search(
    request: Request,
    payload: SavedSearchCreate,
    _claims: dict = Depends(require_user),
) -> dict:
    guard_if_paused()
    user_id = _user_id_from_request(request)
    return create_saved_search(user_id, payload).model_dump()


@app.get('/api/saved-searches/{search_id}')
async def get_search(
    request: Request,
    search_id: str,
    _claims: dict = Depends(require_user),
) -> dict:
    guard_if_paused()
    search = get_saved_search(search_id)
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Search not found')
    return search.model_dump()


@app.delete('/api/saved-searches/{search_id}')
async def delete_search(
    request: Request,
    search_id: str,
    _claims: dict = Depends(require_user),
) -> dict:
    guard_if_paused()
    deleted = delete_saved_search(search_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Search not found')
    return {'deleted': True}


handler = Mangum(app)
