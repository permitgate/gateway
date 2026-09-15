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
from service.exceptions import (
    ApprovalFlowNotFoundError,
    FlowVersionNotFoundError,
)


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


class TestApprovalFlowsServiceCreate:
    """Tests for creating approval flows."""

    async def test_create_flow_minimal(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test creating a flow with required fields."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        assert flow.id is not None
        assert flow.tenant_id == sample_tenant.id
        assert flow.name == "Test Flow"
        assert flow.active_version_id is not None

    async def test_create_flow_with_complex_schema(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test creating a flow with complex JSON schema."""
        json_schema = {
            "type": "object",
            "properties": {
                "user_name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "department": {
                    "type": "string",
                    "enum": ["Sales", "Engineering", "HR"],
                },
                "request_amount": {"type": "number", "minimum": 0},
            },
            "required": ["user_name", "email"],
        }

        preview_schema = {
            "type": "object",
            "properties": {
                "user_name": {"type": "string"},
                "department": {"type": "string"},
            },
        }

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Complex Flow",
            json_schema=json_schema,
            preview_schema=preview_schema,
            schema_validation_enabled=True,
            sla_seconds=7200,
            reset_on_edit=False,
        )

        assert flow.name == "Complex Flow"
        assert flow.active_version_id is not None

    async def test_create_flow_without_validation(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test creating a flow with validation disabled."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="No Validation Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            sla_seconds=1800,
            reset_on_edit=True,
        )

        assert flow.id is not None

    async def test_create_flow_creates_version(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that creating a flow also creates version 1."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Flow With Version",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert len(versions) == 1
        assert versions[0].version == 1
        assert flow.active_version_id == versions[0].id


class TestApprovalFlowsServiceList:
    """Tests for listing approval flows."""

    async def test_list_flows_empty(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test listing flows when none exist."""
        flows = await approval_flows_service.list_flows(test_session, sample_tenant.id)

        assert flows == []

    async def test_list_flows_single(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test listing flows with one flow."""
        created_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        flows = await approval_flows_service.list_flows(test_session, sample_tenant.id)

        assert len(flows) == 1
        assert flows[0].id == created_flow.id
        assert flows[0].name == "Test Flow"

    async def test_list_flows_multiple(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test listing multiple flows."""
        flow1 = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Flow 1",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        flow2 = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Flow 2",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            sla_seconds=7200,
            reset_on_edit=False,
        )

        flows = await approval_flows_service.list_flows(test_session, sample_tenant.id)

        assert len(flows) == 2
        flow_ids = [f.id for f in flows]
        assert flow1.id in flow_ids
        assert flow2.id in flow_ids

    async def test_list_flows_tenant_isolation(
        self, approval_flows_service, test_session
    ):
        """Test that flows are isolated per tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2 = Tenant(id=uuid.uuid4(), name="Tenant 2")
        test_session.add(tenant1)
        test_session.add(tenant2)
        await test_session.commit()

        # Create flow for tenant 1
        await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=tenant1.id,
            name="Tenant 1 Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        # Create flow for tenant 2
        await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=tenant2.id,
            name="Tenant 2 Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        flows_tenant1 = await approval_flows_service.list_flows(
            test_session, tenant1.id
        )
        flows_tenant2 = await approval_flows_service.list_flows(
            test_session, tenant2.id
        )

        assert len(flows_tenant1) == 1
        assert len(flows_tenant2) == 1
        assert flows_tenant1[0].name == "Tenant 1 Flow"
        assert flows_tenant2[0].name == "Tenant 2 Flow"


class TestApprovalFlowsServiceGet:
    """Tests for getting individual flows."""

    async def test_get_flow_found(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test retrieving an existing flow."""
        created_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        retrieved_flow = await approval_flows_service.get_flow(
            test_session, sample_tenant.id, created_flow.id
        )

        assert retrieved_flow.id == created_flow.id
        assert retrieved_flow.name == "Test Flow"

    async def test_get_flow_not_found(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test retrieving a non-existent flow."""
        flow_id = uuid.uuid4()

        with pytest.raises(ApprovalFlowNotFoundError):
            await approval_flows_service.get_flow(
                test_session, sample_tenant.id, flow_id
            )

    async def test_get_flow_wrong_tenant(self, approval_flows_service, test_session):
        """Test that flows cannot be accessed by wrong tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        test_session.add(tenant1)
        await test_session.commit()

        created_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=tenant1.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        tenant2_id = uuid.uuid4()

        with pytest.raises(ApprovalFlowNotFoundError):
            await approval_flows_service.get_flow(
                test_session, tenant2_id, created_flow.id
            )


class TestApprovalFlowsServiceUpdate:
    """Tests for updating approval flows."""

    async def test_update_flow_creates_new_version(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that updating a flow creates a new version."""
        original_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Original Flow",
            json_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        updated_flow = await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=original_flow.id,
            json_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            sla_seconds=7200,
            reset_on_edit=False,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, original_flow.id
        )

        assert len(versions) == 2
        assert versions[0].version == 1
        assert versions[1].version == 2
        assert versions[0].schema_validation_enabled is True
        assert versions[1].schema_validation_enabled is False
        assert versions[0].sla_seconds == 3600
        assert versions[1].sla_seconds == 7200

    async def test_update_flow_updates_active_version(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that updating a flow sets the new version as active."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        original_active_version_id = flow.active_version_id

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=flow.id,
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            sla_seconds=7200,
            reset_on_edit=False,
        )

        # Refresh flow to get updated version
        updated_flow = await approval_flows_service.get_flow(
            test_session, sample_tenant.id, flow.id
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert updated_flow.active_version_id != original_active_version_id
        assert updated_flow.active_version_id == versions[1].id

    async def test_update_flow_not_found(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test updating a non-existent flow."""
        flow_id = uuid.uuid4()

        with pytest.raises(ApprovalFlowNotFoundError):
            await approval_flows_service.update_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                flow_id=flow_id,
                json_schema={"type": "object"},
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_update_multiple_times(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test updating a flow multiple times creates multiple versions."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        # Update 3 times
        for i in range(3):
            await approval_flows_service.update_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                flow_id=flow.id,
                json_schema={"type": "object"},
                preview_schema={"type": "object"},
                schema_validation_enabled=(i % 2 == 0),
                sla_seconds=3600 + (i * 1800),
                reset_on_edit=(i % 2 == 0),
            )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert len(versions) == 4
        assert versions[-1].version == 4


class TestApprovalFlowsServiceVersions:
    """Tests for flow version management."""

    async def test_list_flow_versions_empty(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test listing versions for a flow that doesn't exist."""
        flow_id = uuid.uuid4()

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow_id
        )

        assert versions == []

    async def test_list_flow_versions_single(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test listing versions for a new flow."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert len(versions) == 1
        assert versions[0].version == 1

    async def test_list_flow_versions_ordered(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that versions are returned in order."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        # Create multiple versions
        for _ in range(5):
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

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert len(versions) == 6
        for i, version in enumerate(versions):
            assert version.version == i + 1

    async def test_get_flow_version_found(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test retrieving a specific flow version."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object", "version": 1},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        retrieved_version = await approval_flows_service.get_flow_version(
            test_session, sample_tenant.id, versions[0].id
        )

        assert retrieved_version.id == versions[0].id
        assert retrieved_version.version == 1

    async def test_get_flow_version_not_found(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test retrieving a non-existent flow version."""
        version_id = uuid.uuid4()

        with pytest.raises(FlowVersionNotFoundError):
            await approval_flows_service.get_flow_version(
                test_session, sample_tenant.id, version_id
            )

    async def test_get_flow_version_wrong_tenant(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that versions are isolated per tenant."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        other_tenant_id = uuid.uuid4()

        with pytest.raises(FlowVersionNotFoundError):
            await approval_flows_service.get_flow_version(
                test_session, other_tenant_id, versions[0].id
            )


class TestApprovalFlowsServiceValidation:
    """Tests for flow validation settings."""

    @pytest.mark.parametrize(
        "schema_validation_enabled,sla_seconds,reset_on_edit",
        [
            (True, 3600, True),
            (False, 3600, True),
            (True, 7200, False),
            (False, 1800, False),
            (True, 86400, True),
        ],
    )
    async def test_flow_validation_settings(
        self,
        approval_flows_service,
        test_session,
        sample_tenant,
        schema_validation_enabled,
        sla_seconds,
        reset_on_edit,
    ):
        """Test creating flows with different validation settings."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=schema_validation_enabled,
            sla_seconds=sla_seconds,
            reset_on_edit=reset_on_edit,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert versions[0].schema_validation_enabled == schema_validation_enabled
        assert versions[0].sla_seconds == sla_seconds
        assert versions[0].reset_on_edit == reset_on_edit

    async def test_sla_seconds_variations(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test flows with different SLA values."""
        sla_values = [300, 1800, 3600, 7200, 86400]

        for sla in sla_values:
            flow = await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name=f"Flow SLA {sla}",
                json_schema={"type": "object"},
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                sla_seconds=sla,
                reset_on_edit=True,
            )

            versions = await approval_flows_service.list_flow_versions(
                test_session, sample_tenant.id, flow.id
            )

            assert versions[0].sla_seconds == sla


class TestApprovalFlowsServiceComplexSchemas:
    """Tests for flows with complex JSON schemas."""

    async def test_flow_with_nested_schema(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test creating a flow with nested object schema."""
        json_schema = {
            "type": "object",
            "properties": {
                "request": {
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                            },
                        },
                        "details": {"type": "string"},
                    },
                }
            },
        }

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Nested Schema Flow",
            json_schema=json_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert versions[0].json_schema == json_schema

    async def test_flow_with_array_schema(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test creating a flow with array schema."""
        json_schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                        },
                    },
                }
            },
        }

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Array Schema Flow",
            json_schema=json_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert "items" in versions[0].json_schema["properties"]
        assert versions[0].json_schema["properties"]["items"]["type"] == "array"

    async def test_update_flow_schema_preservation(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that updating a flow preserves schema complexity."""
        original_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }

        updated_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "priority": {"type": "integer"},
            },
        }

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Schema Evolution Flow",
            json_schema=original_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=flow.id,
            json_schema=updated_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert versions[0].json_schema == original_schema
        assert versions[1].json_schema == updated_schema
