"""Live-trading arming gate. Routing real orders requires BOTH credentials present AND
an explicit, deliberately-awkward env flag. Default is unarmed (dry-run). The agent never
arms this — only the human operator does, knowingly."""
from __future__ import annotations
import os
from lowcap_short_system.security.secrets import missing_secrets

ARM_FLAG = "LOWCAP_LIVE_ARMED"
ARM_VALUE = "I_UNDERSTAND_REAL_MONEY"


class LiveNotArmed(RuntimeError):
    pass


def is_armed() -> bool:
    """True only when the operator set the exact arm flag AND all required secrets exist."""
    return os.environ.get(ARM_FLAG) == ARM_VALUE and not missing_secrets()


def require_armed() -> None:
    if not is_armed():
        raise LiveNotArmed(
            "Live trading is not armed. Provide credentials (.env) and set "
            f"{ARM_FLAG}={ARM_VALUE}, then run it yourself. The agent never arms live trading."
        )
