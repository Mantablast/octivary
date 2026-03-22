import os


LOCAL_PROFILE = "local"
AWS_PROFILE = "aws"


def runtime_profile() -> str:
    profile = os.getenv("RUNTIME_PROFILE", LOCAL_PROFILE).strip().lower()
    return profile or LOCAL_PROFILE


def is_local_profile() -> bool:
    return runtime_profile() != AWS_PROFILE


def search_job_store_backend() -> str:
    configured = os.getenv("SEARCH_JOB_STORE_BACKEND", "").strip().lower()
    if configured:
        return configured
    return "local" if is_local_profile() else "dynamodb"


def search_queue_backend() -> str:
    configured = os.getenv("SEARCH_QUEUE_BACKEND", "").strip().lower()
    if configured:
        return configured
    return "local" if is_local_profile() else "sqs"
