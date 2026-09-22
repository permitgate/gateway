# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from config import AppConfig
from service.exceptions import InvalidFlowSchemaError
from service.schema_guard import (
    validate_flow_json_schema,
    validate_flow_preview_schema,
)


class TestSchemaGuardBasics:
    """Tests for basic schema validation."""

    def test_empty_schema_passes(self):
        """Empty schema ({}) is always valid as the no-op sentinel."""
        validate_flow_json_schema({})

    def test_non_dict_schema_rejected(self):
        """Non-dict schemas are rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="must be a dict"):
            validate_flow_json_schema([], config)
        with pytest.raises(InvalidFlowSchemaError, match="must be a dict"):
            validate_flow_json_schema("string", config)
        with pytest.raises(InvalidFlowSchemaError, match="must be a dict"):
            validate_flow_json_schema(1, config)

    def test_missing_schema_dialect(self):
        """Schema without $schema is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="must be"):
            validate_flow_json_schema({"type": "object"}, config)

    def test_wrong_schema_dialect(self):
        """Schema with wrong dialect is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="must be"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "http://json-schema.org/draft-07/schema#",
                },
                config,
            )

    def test_valid_minimal_schema(self):
        """Minimal valid schema with correct $schema passes."""
        config = AppConfig()
        validate_flow_json_schema(
            {
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
            },
            config,
        )


class TestSchemaBannedKeywords:
    """Tests for banned keyword detection."""

    @pytest.mark.parametrize(
        "keyword",
        [
            "$ref",
            "$dynamicRef",
            "$dynamicAnchor",
            "$anchor",
            "$id",
            "$recursiveRef",
            "$recursiveAnchor",
        ],
    )
    def test_banned_keyword_at_root(self, keyword):
        """Banned keywords at root are rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="is not permitted"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    keyword: "value",
                },
                config,
            )

    def test_banned_keyword_in_properties(self):
        """Banned keywords nested in properties are rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="is not permitted"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {"nested": {"$ref": "#/definitions/foo"}},
                },
                config,
            )

    def test_property_named_ref_allowed(self):
        """A property literally named $ref (not a keyword) is allowed."""
        config = AppConfig()
        validate_flow_json_schema(
            {
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "properties": {"$ref": {"type": "string"}},
            },
            config,
        )


class TestSchemaPatternValidation:
    """Tests for pattern/patternProperties regex validation."""

    def test_pattern_too_long_rejected(self):
        """Patterns exceeding max length are rejected."""
        config = AppConfig(flow_schema_max_pattern_length=10)
        with pytest.raises(InvalidFlowSchemaError, match="exceeds max length"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "pattern": "this_pattern_is_way_too_long",
                },
                config,
            )

    def test_pattern_non_re2_compatible_rejected(self):
        """Non-RE2-compatible patterns (e.g. lookaheads) are rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="not RE2-compatible"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "pattern": "(?=.*[A-Z])",
                },
                config,
            )

    def test_valid_pattern_passes(self):
        """Valid RE2-compatible patterns pass."""
        config = AppConfig()
        validate_flow_json_schema(
            {
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "pattern": "^[a-z]+$",
            },
            config,
        )

    def test_patternProperties_validated(self):
        """Patterns in patternProperties are validated."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="not RE2-compatible"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "patternProperties": {"(?=hello)": {"type": "string"}},
                },
                config,
            )


class TestSchemaBounds:
    """Tests for depth and key count bounds."""

    def test_depth_exceeded(self):
        """Schema exceeding max depth is rejected."""
        config = AppConfig(flow_schema_max_depth=2)
        with pytest.raises(InvalidFlowSchemaError, match="exceeds max"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {
                        "level1": {
                            "type": "object",
                            "properties": {
                                "level2": {
                                    "type": "object",
                                    "properties": {"level3": {"type": "string"}},
                                }
                            },
                        }
                    },
                },
                config,
            )

    def test_depth_exceeded_with_nested_combinators(self):
        """Schema with deeply nested allOf/anyOf/oneOf chains exceeds depth limit."""
        config = AppConfig(flow_schema_max_depth=3)
        schema = {
            "type": "object",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "allOf": [
                {
                    "anyOf": [
                        {
                            "oneOf": [
                                {
                                    "properties": {"nested": {"type": "string"}},
                                }
                            ]
                        }
                    ]
                }
            ],
        }
        with pytest.raises(InvalidFlowSchemaError, match="exceeds max"):
            validate_flow_json_schema(schema, config)

    def test_keys_exceeded(self):
        """Schema exceeding max keys is rejected."""
        config = AppConfig(flow_schema_max_keys=2)
        with pytest.raises(InvalidFlowSchemaError, match="exceeds max"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {
                        "key1": {"type": "string"},
                        "key2": {"type": "string"},
                        "key3": {"type": "string"},
                    },
                },
                config,
            )

    def test_size_exceeded(self):
        """Schema exceeding max size is rejected."""
        config = AppConfig(flow_schema_max_size_bytes=50)
        with pytest.raises(InvalidFlowSchemaError, match="exceeds max"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {
                        "very_long_property_name_to_exceed_size": {"type": "string"},
                    },
                },
                config,
            )


class TestSchemaMalformed:
    """Tests for malformed schema detection."""

    def test_malformed_required_array(self):
        """Malformed 'required' (not an array) is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="validation failed"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "required": "name",
                },
                config,
            )


class TestSchemaNonSerializable:
    """Tests for non-JSON-serializable values (NaN, Infinity, etc.)."""

    def test_json_schema_with_nan_rejected(self):
        """JSON schema containing NaN is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="non-JSON-serializable"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {"value": {"type": "number", "default": math.nan}},
                },
                config,
            )

    def test_json_schema_with_infinity_rejected(self):
        """JSON schema containing Infinity is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="non-JSON-serializable"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {"value": {"type": "number", "maximum": math.inf}},
                },
                config,
            )

    def test_json_schema_with_negative_infinity_rejected(self):
        """JSON schema containing negative Infinity is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="non-JSON-serializable"):
            validate_flow_json_schema(
                {
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {"value": {"type": "number", "minimum": -math.inf}},
                },
                config,
            )

    def test_preview_schema_with_nan_rejected(self):
        """Preview schema containing NaN is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="non-JSON-serializable"):
            validate_flow_preview_schema(
                {"fields": [{"name": "value", "default": math.nan}]},
                config,
            )

    def test_preview_schema_with_infinity_rejected(self):
        """Preview schema containing Infinity is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="non-JSON-serializable"):
            validate_flow_preview_schema(
                {"fields": [{"name": "value", "max": math.inf}]},
                config,
            )

    def test_preview_schema_malformed_type_rejected(self):
        """Malformed preview schema with invalid type field is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="not a valid JSON Schema"):
            validate_flow_preview_schema(
                {"type": 7},
                config,
            )

    def test_preview_schema_malformed_required_rejected(self):
        """Malformed preview schema with required as string instead of array is rejected."""
        config = AppConfig()
        with pytest.raises(InvalidFlowSchemaError, match="not a valid JSON Schema"):
            validate_flow_preview_schema(
                {"type": "object", "required": "name"},
                config,
            )

    def test_preview_schema_valid_passes(self):
        """Valid preview schema passes."""
        config = AppConfig()
        validate_flow_preview_schema(
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number"},
                },
            },
            config,
        )
