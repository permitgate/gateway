# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from db.models import Tenant, User
from model import ApprovalStepInput
from service.approval_flows_service import ApprovalFlowsService
from service.approval_steps_service import ApprovalStepsService
from service.exceptions import (
    ApprovalFlowNotFoundError,
    FlowVersionNotFoundError,
    InvalidApprovalStepError,
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


@pytest.fixture
async def sample_user(test_session, sample_tenant):
    """Create a sample user."""
    user = User(id=uuid.uuid4(), tenant_id=sample_tenant.id, email="reviewer@test.com")
    test_session.add(user)
    await test_session.commit()
    return user


@pytest.fixture
def minimal_valid_schema():
    """Return a minimal valid JSON schema."""
    return {
        "type": "object",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
    }


class TestApprovalFlowsServiceCreate:
    """Tests for creating approval flows."""

    async def test_create_flow_minimal(
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test creating a flow with required fields."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
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
        assert flow.tenant_id == sample_tenant.id
        assert flow.name == "Test Flow"
        assert flow.active_version_id is not None

    async def test_create_flow_with_complex_schema(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test creating a flow with complex JSON schema."""
        json_schema = {
            "type": "object",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
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
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
            json_schema={},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=1800,
            reset_on_edit=True,
        )

        assert flow.id is not None

    async def test_create_flow_creates_version(
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test that creating a flow also creates version 1."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Flow With Version",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test listing flows with one flow."""
        created_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        flows = await approval_flows_service.list_flows(test_session, sample_tenant.id)

        assert len(flows) == 1
        assert flows[0].id == created_flow.id
        assert flows[0].name == "Test Flow"

    async def test_list_flows_multiple(
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test listing multiple flows."""
        flow1 = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Flow 1",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        flow2 = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Flow 2",
            json_schema={},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=7200,
            reset_on_edit=False,
        )

        flows = await approval_flows_service.list_flows(test_session, sample_tenant.id)

        assert len(flows) == 2
        flow_ids = [f.id for f in flows]
        assert flow1.id in flow_ids
        assert flow2.id in flow_ids

    async def test_list_flows_tenant_isolation(
        self, approval_flows_service, test_session, minimal_valid_schema
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
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        # Create flow for tenant 2
        await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=tenant2.id,
            name="Tenant 2 Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test retrieving an existing flow."""
        created_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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

    async def test_get_flow_wrong_tenant(
        self, approval_flows_service, test_session, minimal_valid_schema
    ):
        """Test that flows cannot be accessed by wrong tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        test_session.add(tenant1)
        await test_session.commit()

        created_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=tenant1.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
            json_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "$schema": "https://json-schema.org/draft/2020-12/schema",
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

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=original_flow.id,
            json_schema={},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test that updating a flow sets the new version as active."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        original_active_version_id = flow.active_version_id

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=flow.id,
            json_schema={},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test updating a non-existent flow."""
        flow_id = uuid.uuid4()

        with pytest.raises(ApprovalFlowNotFoundError):
            await approval_flows_service.update_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                flow_id=flow_id,
                json_schema=minimal_valid_schema,
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
            )

    async def test_update_multiple_times(
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test updating a flow multiple times creates multiple versions."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={
                "type": "object",
            },
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        # Update 3 times
        for i in range(3):
            is_enabled = i % 2 == 0
            await approval_flows_service.update_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                flow_id=flow.id,
                json_schema=minimal_valid_schema if is_enabled else {},
                preview_schema={"type": "object"},
                schema_validation_enabled=is_enabled,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600 + (i * 1800),
                reset_on_edit=is_enabled,
            )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert len(versions) == 4
        assert versions[-1].version == 4

    async def test_update_flow_amount_and_currency_paths(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that updating flow updates amount_path and currency_path."""
        original_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Original Flow",
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path="/original/amount",
            currency_path="/original/currency",
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=original_flow.id,
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path="/updated/amount",
            currency_path="/updated/currency",
            high_risk=True,
            currency_exchange_rates={"USD": 1.0, "EUR": 0.92},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, original_flow.id
        )

        assert len(versions) == 2
        assert versions[0].amount_path == "/original/amount"
        assert versions[0].currency_path == "/original/currency"
        assert versions[0].high_risk is False
        assert versions[0].currency_exchange_rates == {}
        assert versions[1].amount_path == "/updated/amount"
        assert versions[1].currency_path == "/updated/currency"
        assert versions[1].high_risk is True
        assert versions[1].currency_exchange_rates == {"USD": 1.0, "EUR": 0.92}

    async def test_update_flow_high_risk_flag(
        self, approval_flows_service, test_session, sample_tenant
    ):
        """Test that updating flow updates high_risk flag."""
        original_flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Original Flow",
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
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

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=original_flow.id,
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
            },
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=True,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, original_flow.id
        )

        assert len(versions) == 2
        assert versions[0].high_risk is False
        assert versions[1].high_risk is True


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
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test listing versions for a new flow."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert len(versions) == 1
        assert versions[0].version == 1

    async def test_list_flow_versions_ordered(
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test that versions are returned in order."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        # Create multiple versions
        for _ in range(5):
            await approval_flows_service.update_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                flow_id=flow.id,
                json_schema=minimal_valid_schema,
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
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
            json_schema={
                "type": "object",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
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
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test that versions are isolated per tenant."""
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
        minimal_valid_schema,
    ):
        """Test creating flows with different validation settings."""
        json_schema = minimal_valid_schema if schema_validation_enabled else {}
        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Flow",
            json_schema=json_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=schema_validation_enabled,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
        self, approval_flows_service, test_session, sample_tenant, minimal_valid_schema
    ):
        """Test flows with different SLA values."""
        sla_values = [300, 1800, 3600, 7200, 86400]

        for sla in sla_values:
            flow = await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name=f"Flow SLA {sla}",
                json_schema=minimal_valid_schema,
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
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
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        }

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Nested Schema Flow",
            json_schema=json_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        }

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Array Schema Flow",
            json_schema=json_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
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
            "$schema": "https://json-schema.org/draft/2020-12/schema",
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
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        }

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Schema Evolution Flow",
            json_schema=original_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
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
            json_schema=updated_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
        )

        versions = await approval_flows_service.list_flow_versions(
            test_session, sample_tenant.id, flow.id
        )

        assert versions[0].json_schema == original_schema
        assert versions[1].json_schema == updated_schema


class TestApprovalFlowsServiceSteps:
    """Tests for creating and managing approval steps."""

    async def test_create_flow_with_steps(
        self,
        approval_flows_service,
        test_session,
        sample_tenant,
        sample_user,
        minimal_valid_schema,
    ):
        """Test creating a flow with approval steps."""
        steps = [
            ApprovalStepInput(
                name="Manager Review",
                target_user_id=sample_user.id,
                editable_paths=["/description"],
            )
        ]

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Flow With Steps",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
            steps=steps,
        )

        assert flow.id is not None
        assert flow.active_version_id is not None

        # Verify steps were created
        steps_service = ApprovalStepsService()
        flow_steps = await steps_service.list_steps_for_flow_version(
            test_session, sample_tenant.id, flow.active_version_id
        )

        assert len(flow_steps) == 1
        assert flow_steps[0].name == "Manager Review"
        assert flow_steps[0].target_user_id == sample_user.id
        assert flow_steps[0].step_order == 1

    async def test_step_ordering_is_sequential(
        self,
        approval_flows_service,
        test_session,
        sample_tenant,
        sample_user,
        minimal_valid_schema,
    ):
        """Test that step_order is assigned sequentially."""
        steps = [
            ApprovalStepInput(
                name="Step 1",
                target_user_id=sample_user.id,
                editable_paths=[],
            ),
            ApprovalStepInput(
                name="Step 2",
                target_user_id=sample_user.id,
                editable_paths=[],
            ),
            ApprovalStepInput(
                name="Step 3",
                target_user_id=sample_user.id,
                editable_paths=[],
            ),
        ]

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Multi-Step Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
            steps=steps,
        )

        steps_service = ApprovalStepsService()
        flow_steps = await steps_service.list_steps_for_flow_version(
            test_session, sample_tenant.id, flow.active_version_id
        )

        assert len(flow_steps) == 3
        assert flow_steps[0].step_order == 1
        assert flow_steps[1].step_order == 2
        assert flow_steps[2].step_order == 3

    async def test_invalid_step_amount_without_path(
        self,
        approval_flows_service,
        test_session,
        sample_tenant,
        sample_user,
        minimal_valid_schema,
    ):
        """Test that step with amount_limit_minor_units fails when flow has no amount_path."""
        steps = [
            ApprovalStepInput(
                name="Step With Amount",
                target_user_id=sample_user.id,
                editable_paths=[],
                amount_limit_minor_units=1000,
                currency="USD",
            )
        ]

        with pytest.raises(InvalidApprovalStepError):
            await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name="Invalid Flow",
                json_schema=minimal_valid_schema,
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path=None,
                currency_path=None,
                high_risk=False,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
                steps=steps,
            )

    async def test_high_risk_flow_requires_step_amounts(
        self,
        approval_flows_service,
        test_session,
        sample_tenant,
        sample_user,
        minimal_valid_schema,
    ):
        """Test that high_risk flow requires all steps to have amount_limit_minor_units."""
        steps = [
            ApprovalStepInput(
                name="Step Without Amount",
                target_user_id=sample_user.id,
                editable_paths=[],
            )
        ]

        with pytest.raises(InvalidApprovalStepError):
            await approval_flows_service.create_flow(
                session=test_session,
                tenant_id=sample_tenant.id,
                name="High Risk Flow",
                json_schema=minimal_valid_schema,
                preview_schema={"type": "object"},
                schema_validation_enabled=True,
                amount_path="/amount",
                currency_path="/currency",
                high_risk=True,
                currency_exchange_rates={},
                sla_seconds=3600,
                reset_on_edit=True,
                steps=steps,
            )

    async def test_update_flow_creates_steps_for_new_version(
        self,
        approval_flows_service,
        test_session,
        sample_tenant,
        sample_user,
        minimal_valid_schema,
    ):
        """Test that update_flow creates steps for the new version."""
        initial_steps = [
            ApprovalStepInput(
                name="Initial Step",
                target_user_id=sample_user.id,
                editable_paths=[],
            )
        ]

        flow = await approval_flows_service.create_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Updateable Flow",
            json_schema=minimal_valid_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
            steps=initial_steps,
        )

        updated_schema = {
            "type": "object",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "properties": {"field": {"type": "string"}},
        }

        new_steps = [
            ApprovalStepInput(
                name="Updated Step",
                target_user_id=sample_user.id,
                editable_paths=["/field"],
            )
        ]

        await approval_flows_service.update_flow(
            session=test_session,
            tenant_id=sample_tenant.id,
            flow_id=flow.id,
            json_schema=updated_schema,
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            amount_path=None,
            currency_path=None,
            high_risk=False,
            currency_exchange_rates={},
            sla_seconds=3600,
            reset_on_edit=True,
            steps=new_steps,
        )

        # Get the new active version
        updated_flow = await approval_flows_service.get_flow(
            test_session, sample_tenant.id, flow.id
        )

        steps_service = ApprovalStepsService()
        new_version_steps = await steps_service.list_steps_for_flow_version(
            test_session, sample_tenant.id, updated_flow.active_version_id
        )

        assert len(new_version_steps) == 1
        assert new_version_steps[0].name == "Updated Step"
