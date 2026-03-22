import json
import os
import threading
from typing import Any, Callable

from .runtime import search_queue_backend

_BOTO3_AVAILABLE = False

try:
    import boto3  # type: ignore

    _BOTO3_AVAILABLE = True
except Exception:
    _BOTO3_AVAILABLE = False


class LocalQueueProvider:
    def __init__(self, handler: Callable[[dict[str, Any]], None]) -> None:
        self.handler = handler

    def enqueue(self, payload: dict[str, Any]) -> None:
        thread = threading.Thread(target=self.handler, args=(payload,), daemon=True)
        thread.start()


class SqsQueueProvider:
    def __init__(self, handler: Callable[[dict[str, Any]], None], queue_url: str) -> None:
        self.handler = handler
        self.queue_url = queue_url
        self.client = boto3.client("sqs")

    def enqueue(self, payload: dict[str, Any]) -> None:
        self.client.send_message(QueueUrl=self.queue_url, MessageBody=json.dumps(payload))


_QUEUE_PROVIDER: object | None = None


def get_queue_provider(handler: Callable[[dict[str, Any]], None]) -> object:
    global _QUEUE_PROVIDER
    if _QUEUE_PROVIDER is not None:
        return _QUEUE_PROVIDER

    backend = search_queue_backend()
    if backend == "sqs" and _BOTO3_AVAILABLE:
        queue_url = os.getenv("SEARCH_JOBS_QUEUE_URL")
        if queue_url:
            _QUEUE_PROVIDER = SqsQueueProvider(handler, queue_url)
            return _QUEUE_PROVIDER

    _QUEUE_PROVIDER = LocalQueueProvider(handler)
    return _QUEUE_PROVIDER
