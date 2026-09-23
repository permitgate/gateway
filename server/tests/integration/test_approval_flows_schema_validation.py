# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from db.models import Tenant
from service.approval_flows_service import ApprovalFlowsService
from service.exceptions import InvalidFlowSchemaError


@pytest.fixture
def approval_flows_service():
    """Create an ApprovalFlowsService instance."""
    return ApprovalFlowsService()


@pytest.fixture
async def sample_tenant(test_session):
    """Create a sample tenant."""
    tenant = Tenant(id=uuid.uuid4(), name="Test Tenant")
    test_session.add(tenant)
    await test_session.commit()
    return tenant


class TestApprovalFlowsServiceSchemaValidation:
    """Tests for flow schema validation at the service layer."""

    async def test_create_flow_missing_schema_rejected(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Flow creation with missing $schema is rejected."""
        with pytest.raises(InvalidFlowSchemaError, match="must be"):
            await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name="Bad Flow",
                json_schema={"type": "object"},
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_create_flow_banned_ref_rejected(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Flow creation with $ref is rejected."""
        with pytest.raises(InvalidFlowSchemaError, match="not permitted"):
            await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name="Bad Flow",
                json_schema={
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": "#/definitions/foo",
                },
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_create_flow_coherence_check_enabled_empty_rejected(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Flow with schema_validation_enabled=True and empty json_schema is rejected."""
        with pytest.raises(
            InvalidFlowSchemaError,
            match="must not be empty when schema_validation_enabled is true",
        ):
            await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name="Bad Flow",
                json_schema={},
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_create_flow_coherence_check_disabled_nonempty_rejected(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Flow with schema_validation_enabled=False and non-empty json_schema is rejected."""
        with pytest.raises(
            InvalidFlowSchemaError,
            match="must be {} when schema_validation_enabled is false",
        ):
            await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name="Bad Flow",
                json_schema={
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                },
                preview_schema={"type": "object"},
                schema_validation_enabled=False,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_update_flow_missing_schema_rejected(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Flow update with missing $schema is rejected."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Original Flow",
            json_schema={},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        with pytest.raises(InvalidFlowSchemaError, match="must be"):
            await approval_flows_service.update_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                flow_id=flow.id,
                json_schema={"type": "object"},
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_create_flow_valid_schema_passes(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Valid schema passes."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Good Flow",
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "properties": {"name": {"type": "string"}},
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )
        assert flow.id is not None

    async def test_create_flow_database_size_constraint_error_handled(
        self, approval_flows_service, test_session, sample_tenant, monkeypatch
    ):
        """Database IntegrityError for schema size constraint is caught and converted to InvalidFlowSchemaError."""

        from sqlalchemy.exc import IntegrityError

        # Mock the repository to raise IntegrityError with the schema size constraint
        original_create_flow_version = (
            approval_flows_service._version_repo.create_flow_version
        )

        call_count = [0]

        async def mock_create_flow_version(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return await original_create_flow_version(*args, **kwargs)

        monkeypatch.setattr(
            approval_flows_service._version_repo,
            "create_flow_version",
            mock_create_flow_version,
        )

        # Create a flow with schema that would pass service-side validation
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Good Flow",
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "properties": {"name": {"type": "string"}},
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        # Now update with mock that raises IntegrityError
        async def mock_create_flow_version_update(*args, **kwargs):
            exc = IntegrityError(
                'new row for relation "flow_versions" violates check constraint "chk_flow_version_json_schema_shape"',
                None,
                None,
            )
            raise exc

        monkeypatch.setattr(
            approval_flows_service._version_repo,
            "create_flow_version",
            mock_create_flow_version_update,
        )

        # Should convert IntegrityError to InvalidFlowSchemaError
        with pytest.raises(InvalidFlowSchemaError, match="exceeds maximum size"):
            await approval_flows_service.update_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                flow_id=flow.id,
                json_schema={
                    "type": "object",
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {"name": {"type": "string"}},
                },
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_create_flow_with_financial_fields(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test creating flow with financial fields."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Financial Flow",
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "properties": {"amount": {"type": "number"}},
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path="/request/amount",
            currency_path="/request/currency",
            high_risk=True,
            currency_exchange_rates={"USD": 1.0, "EUR": 0.92, "GBP": 0.80},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert versions[0].amount_path == "/request/amount"
        assert versions[0].currency_path == "/request/currency"
        assert versions[0].high_risk is True
        assert versions[0].currency_exchange_rates == {
            "USD": 1.0,
            "EUR": 0.92,
            "GBP": 0.80,
        }

    async def test_update_flow_financial_fields(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test updating flow financial fields."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Financial Flow",
            json_schema={},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=flow.id,
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "properties": {"amount": {"type": "number"}},
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path="/amount",
            currency_path="/currency",
            high_risk=True,
            currency_exchange_rates={"JPY": 110.0, "CNY": 6.5},
            sla_seconds=7200,
            reset_on_edit=False,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert len(versions) == 2
        assert versions[1].amount_path == "/amount"
        assert versions[1].currency_path == "/currency"
        assert versions[1].high_risk is True
        assert versions[1].currency_exchange_rates == {"JPY": 110.0, "CNY": 6.5}
