# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

"""JSON Schema validation guard for flow_versions.json_schema.

Enforces structural, dialect, and bounds constraints on flow JSON schemas to ensure:
- Immutability: schemas pinned to Draft 2020-12, never silently changing semantics on validator upgrade.
- Determinism: compiled with the real validator at creation, not at validation time.
- Safety: no SSRF via $ref, no ReDoS via pattern, no resource exhaustion via depth/key count.
- Simplicity: format is annotation-only, never assertion; $ref/dynamic anchors banned outright.
"""

import json
from typing import Any

import re2
from jsonschema import Draft202012Validator, validators

from config import AppConfig
from service.exceptions import InvalidFlowSchemaError

_ALLOWED_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

_BANNED_KEYWORDS = {
    "$ref",
    "$dynamicRef",
    "$dynamicAnchor",
    "$anchor",
    "$id",
    "$recursiveRef",
    "$recursiveAnchor",
}

_DEPTH_MAP_KEYS = {"properties", "dependentSchemas"}
_DEPTH_SINGLE_KEYS = {
    "items",
    "additionalProperties",
    "unevaluatedItems",
    "unevaluatedProperties",
    "contentSchema",
}
_LIST_ITEM_KEYS = {"prefixItems"}
_FLAT_MAP_KEYS = {"$defs", "definitions"}
_NO_DEPTH_LIST_KEYS = {"allOf", "anyOf", "oneOf"}
_NO_DEPTH_SINGLE_KEYS = {
    "not",
    "if",
    "then",
    "else",
    "contains",
    "propertyNames",
}


def _re2_pattern_validator(validator, pattern, instance, schema):
    """Validate that a string instance matches the RE2 pattern."""
    if not isinstance(instance, str):
        return
    try:
        if re2.search(pattern, instance):
            return
    except re2.error as exc:
        yield f"pattern {pattern!r} failed RE2 compilation: {exc}"
        return
    yield f"{instance!r} does not match RE2 pattern {pattern!r}"


class _Stats:
    def __init__(self):
        self.max_depth = 0
        self.total_keys = 0


def _check_pattern(pattern: Any, path: str, config: AppConfig) -> None:
    """Validate a regex pattern against length and RE2 compatibility."""
    if not isinstance(pattern, str):
        raise InvalidFlowSchemaError(
            f"pattern at {path} must be a string, got {type(pattern).__name__}"
        )
    if len(pattern) > config.flow_schema_max_pattern_length:
        raise InvalidFlowSchemaError(
            f"pattern at {path} exceeds max length {config.flow_schema_max_pattern_length}"
        )
    try:
        re2.compile(pattern)
    except re2.error as exc:
        raise InvalidFlowSchemaError(
            f"pattern at {path} is not RE2-compatible: {exc}"
        ) from exc


def _walk_schema(
    schema: Any, depth: int, stats: _Stats, path: str, config: AppConfig
) -> None:
    """Recursively validate schema structure, tracking depth and key count.

    Enforces depth limit before recursing to prevent resource exhaustion.
    """
    if not isinstance(schema, dict):
        return

    if depth > config.flow_schema_max_depth:
        raise InvalidFlowSchemaError(
            f"schema nesting depth {depth} exceeds max {config.flow_schema_max_depth}"
        )

    stats.max_depth = max(stats.max_depth, depth)
    stats.total_keys += len(schema)

    for key, value in schema.items():
        if key in _BANNED_KEYWORDS or (key == "$schema" and path):
            raise InvalidFlowSchemaError(f"'{key}' is not permitted (at {path or '/'})")

        if isinstance(value, list):
            stats.total_keys += len(value)

        if key == "pattern":
            _check_pattern(value, f"{path}/pattern", config)
        elif key == "patternProperties" and isinstance(value, dict):
            for pattern, subschema in value.items():
                stats.total_keys += 1
                _check_pattern(pattern, f"{path}/patternProperties/{pattern}", config)
                _walk_schema(
                    subschema,
                    depth + 1,
                    stats,
                    f"{path}/patternProperties/{pattern}",
                    config,
                )
        elif (
            key in _DEPTH_MAP_KEYS
            and isinstance(value, dict)
            or key in _FLAT_MAP_KEYS
            and isinstance(value, dict)
        ):
            for name, subschema in value.items():
                stats.total_keys += 1
                _walk_schema(
                    subschema, depth + 1, stats, f"{path}/{key}/{name}", config
                )
        elif key in _DEPTH_SINGLE_KEYS:
            _walk_schema(value, depth + 1, stats, f"{path}/{key}", config)
        elif (
            key in _LIST_ITEM_KEYS
            and isinstance(value, list)
            or key in _NO_DEPTH_LIST_KEYS
            and isinstance(value, list)
        ):
            for i, item in enumerate(value):
                stats.total_keys += 1
                _walk_schema(item, depth + 1, stats, f"{path}/{key}/{i}", config)
        elif key in _NO_DEPTH_SINGLE_KEYS:
            _walk_schema(value, depth + 1, stats, f"{path}/{key}", config)


def validate_flow_preview_schema(
    preview_schema: dict, config: AppConfig | None = None
) -> None:
    """Validate a flow version preview schema (safe field allowlist).

    Preview schemas are simplified field allowlists, so they have fewer constraints than json_schema.
    They must be valid objects but don't require $schema pinning or full JSON Schema semantics.

    Raises InvalidFlowSchemaError on any violation.

    Args:
        preview_schema: The preview schema to validate.
        config: AppConfig instance for limits; if None, uses get_app_config().
    """
    from config import get_app_config

    if config is None:
        config = get_app_config()

    if not isinstance(preview_schema, dict):
        raise InvalidFlowSchemaError(
            f"preview_schema must be a dict, got {type(preview_schema).__name__}"
        )

    try:
        serialized = json.dumps(
            preview_schema, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidFlowSchemaError(
            f"preview_schema contains non-JSON-serializable values: {exc}"
        ) from exc
    if len(serialized) > config.flow_schema_max_size_bytes:
        raise InvalidFlowSchemaError(
            f"preview_schema size {len(serialized)} exceeds max {config.flow_schema_max_size_bytes}"
        )


def validate_flow_json_schema(
    json_schema: dict, config: AppConfig | None = None
) -> None:
    """Validate a flow version JSON schema against all structural and semantic constraints.

    Raises InvalidFlowSchemaError on any violation.

    Args:
        json_schema: The JSON schema to validate.
        config: AppConfig instance for limits; if None, uses get_app_config().
    """
    from config import get_app_config

    if config is None:
        config = get_app_config()

    if not isinstance(json_schema, dict):
        raise InvalidFlowSchemaError(
            f"json_schema must be a dict, got {type(json_schema).__name__}"
        )

    if json_schema == {}:
        return

    if json_schema.get("$schema") != _ALLOWED_SCHEMA_DIALECT:
        raise InvalidFlowSchemaError(
            f'$schema must be "{_ALLOWED_SCHEMA_DIALECT}", got {json_schema.get("$schema")}'
        )

    try:
        serialized = json.dumps(
            json_schema, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidFlowSchemaError(
            f"json_schema contains non-JSON-serializable values: {exc}"
        ) from exc
    if len(serialized) > config.flow_schema_max_size_bytes:
        raise InvalidFlowSchemaError(
            f"json_schema size {len(serialized)} exceeds max {config.flow_schema_max_size_bytes}"
        )

    stats = _Stats()
    _walk_schema(json_schema, 0, stats, "", config)

    if stats.total_keys > config.flow_schema_max_keys:
        raise InvalidFlowSchemaError(
            f"schema total keys {stats.total_keys} exceeds max {config.flow_schema_max_keys}"
        )

    try:
        Draft202012Validator.check_schema(json_schema)
    except Exception as exc:
        raise InvalidFlowSchemaError(f"schema validation failed: {exc}") from exc

    try:
        all_validators = dict(Draft202012Validator.VALIDATORS)
        all_validators["pattern"] = _re2_pattern_validator
        RE2Draft202012Validator = validators.create(
            meta_schema=Draft202012Validator.META_SCHEMA,
            validators=all_validators,
        )
        RE2Draft202012Validator(json_schema)
    except Exception as exc:
        raise InvalidFlowSchemaError(f"schema compilation failed: {exc}") from exc
