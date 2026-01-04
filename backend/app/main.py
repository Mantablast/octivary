import os

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from .config_loader import list_config_keys, load_filter_config
from .cost_guardrail import guard_if_paused
from .models import ItemsRequest, ItemResult, SavedSearchCreate
from .provider_registry import resolve_provider
from .storage import (
    create_saved_search,
    delete_saved_search,
    get_saved_search,
    list_saved_searches,
)

app = FastAPI(title='Octivary API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


def _user_id_from_request(request: Request) -> str:
    return request.headers.get('x-user-id', 'demo-user')


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


@app.post('/api/items', response_model=list[ItemResult])
async def get_items(payload: ItemsRequest) -> list[ItemResult]:
    guard_if_paused()
    config = load_filter_config(payload.config_key)
    provider_key = config['datasets']['primary']['data_source']['provider_key']
    resolve_provider(provider_key)
    return [
        ItemResult(item_id='item-1', title='Featured listing', score=88.0, price=420),
        ItemResult(item_id='item-2', title='Best value pick', score=80.0, price=310),
        ItemResult(item_id='item-3', title='Premium option', score=92.0, price=680),
    ]


@app.get('/api/saved-searches')
async def get_saved_searches(request: Request) -> list[dict]:
    guard_if_paused()
    user_id = _user_id_from_request(request)
    return [search.model_dump() for search in list_saved_searches(user_id)]


@app.post('/api/saved-searches')
async def create_search(request: Request, payload: SavedSearchCreate) -> dict:
    guard_if_paused()
    user_id = _user_id_from_request(request)
    return create_saved_search(user_id, payload).model_dump()


@app.get('/api/saved-searches/{search_id}')
async def get_search(request: Request, search_id: str) -> dict:
    guard_if_paused()
    search = get_saved_search(search_id)
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Search not found')
    return search.model_dump()


@app.delete('/api/saved-searches/{search_id}')
async def delete_search(request: Request, search_id: str) -> dict:
    guard_if_paused()
    deleted = delete_saved_search(search_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Search not found')
    return {'deleted': True}


handler = Mangum(app)
