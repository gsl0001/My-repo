"""Secrets handling. Keys come from the environment only — never the repo. Copy
`.env.example` to `.env` (gitignored) for local dev. Fail loudly on a missing secret."""
from __future__ import annotations
import os


class MissingSecret(RuntimeError):
    pass


# Secrets the live system will need (Phase 3). Names only — never values.
REQUIRED_SECRETS = (
    "TRADEZERO_API_KEY",
    "TRADEZERO_API_SECRET",
    "POLYGON_API_KEY",
)


def get_secret(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise MissingSecret(
            f"Required secret '{name}' is not set. See .env.example; never commit secrets."
        )
    return val


def missing_secrets(names: tuple[str, ...] = REQUIRED_SECRETS) -> list[str]:
    return [n for n in names if not os.environ.get(n)]
