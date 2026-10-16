"""Release boundary shared by API entry points and the orchestrator."""
from fastapi import HTTPException

DEFERRED_ACTIONS = frozenset({'tailor', 'curate', 'research'})


def unavailable():
    raise HTTPException(404, 'This feature is not available in the core release.')


def require_core_action(action: str):
    if action in DEFERRED_ACTIONS:
        unavailable()


def core_features() -> dict:
    return {'search': True, 'tracker': True, 'preparation': False,
            'learning': False, 'manual_linkedin': False}
