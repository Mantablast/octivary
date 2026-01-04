import os
from fastapi import HTTPException, status


def guard_if_paused() -> None:
    if os.getenv('OCTIVARY_PAUSED') == '1' or os.getenv('BUDGET_EXCEEDED') == '1':
        max_cost = os.getenv('MAX_MONTHLY_COST', '50')
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'Service paused to respect the ${max_cost} monthly budget.',
        )
