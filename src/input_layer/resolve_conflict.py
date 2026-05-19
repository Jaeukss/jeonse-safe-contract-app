from __future__ import annotations

from typing import Any


def build_resolution_map(user_choices: dict[str, Any] | None) -> dict[str, Any]:
    if not user_choices:
        return {}
    return {field: value for field, value in user_choices.items() if value not in {None, "사용 안 함"}}
