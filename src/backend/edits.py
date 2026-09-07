"""Apply staff JSON-pointer edits and re-apply them after later AI updates."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .errors import ApiError


def _unescape(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _parse_path(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ApiError(422, "INVALID_EDIT_PATH", "Edit paths must be JSON Pointers.")
    if path == "/":
        return []
    return [_unescape(part) for part in path.split("/")[1:]]


def _parent_and_key(document: Any, path: str) -> tuple[Any, str | int]:
    parts = _parse_path(path)
    if not parts:
        raise ApiError(422, "INVALID_EDIT_PATH", "The document root cannot be replaced by a staff edit.")
    current = document
    for part in parts[:-1]:
        key: Any = int(part) if isinstance(current, list) and part.isdigit() else part
        try:
            current = current[key]
        except (KeyError, IndexError, TypeError) as exc:
            raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.") from exc
    last = parts[-1]
    if isinstance(current, list) and last.isdigit():
        return current, int(last)
    return current, last


def apply_edits(document: dict[str, Any], edits: list[dict[str, Any]]) -> dict[str, Any]:
    result = deepcopy(document)
    for edit in edits:
        op = edit.get("op")
        path = edit.get("path")
        if not isinstance(path, str):
            raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.")
        parent, key = _parent_and_key(result, path)
        if op == "replace":
            if isinstance(parent, list):
                if not isinstance(key, int) or key >= len(parent) or key < 0:
                    raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.")
                parent[key] = deepcopy(edit.get("value"))
            elif isinstance(parent, dict):
                if key not in parent:
                    raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.")
                parent[key] = deepcopy(edit.get("value"))
            else:
                raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.")
        elif op == "add":
            if isinstance(parent, list):
                if key == "-" or key == len(parent):
                    parent.append(deepcopy(edit.get("value")))
                elif isinstance(key, int) and 0 <= key <= len(parent):
                    parent.insert(key, deepcopy(edit.get("value")))
                else:
                    raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.")
            elif isinstance(parent, dict):
                parent[str(key)] = deepcopy(edit.get("value"))
            else:
                raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.")
        elif op == "remove":
            try:
                if isinstance(parent, list) and isinstance(key, int):
                    parent.pop(key)
                else:
                    del parent[key]
            except (KeyError, IndexError, TypeError) as exc:
                raise ApiError(422, "INVALID_EDIT_PATH", "The edit path does not exist on this case.") from exc
        else:
            raise ApiError(422, "INVALID_EDIT_PATH", "The edit operation is not supported.")
    return result
