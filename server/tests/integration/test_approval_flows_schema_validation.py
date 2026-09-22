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
            sla_seconds=3600,
            reset_on_edit=True,
        )
        assert flow.id is not None
