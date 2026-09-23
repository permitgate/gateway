# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.approval_flows import router
from db import get_session
from db.models import ApprovalFlow, FlowVersion
from service.exceptions import (
    ApprovalFlowNotFoundError,
    FlowVersionNotFoundError,
    NoActiveVersionError,
)


@pytest.fixture
def client(mock_session):
    """Create a test client for the approval_flows router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Mock the get_session dependency
    app.dependency_overrides[get_session] = lambda: mock_session

    return TestClient(app)


@pytest.fixture
def sample_tenant_id():
    """Create a sample tenant ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_flow_id():
    """Create a sample flow ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_version_id():
    """Create a sample version ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_approval_flow(sample_tenant_id, sample_flow_id):
    """Create a sample ApprovalFlow object."""
    return ApprovalFlow(
        id=sample_flow_id,
        tenant_id=sample_tenant_id,
        name="Test Flow",
        active_version_id=uuid.uuid4(),
        created_at=datetime.now(tz=UTC),
    )


@pytest.fixture
def sample_flow_version(sample_tenant_id, sample_flow_id, sample_version_id):
    """Create a sample FlowVersion object."""
    return FlowVersion(
        id=sample_version_id,
        tenant_id=sample_tenant_id,
        flow_id=sample_flow_id,
        version=1,
        json_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        preview_schema={"type": "object"},
        schema_validation_enabled=True,
        amount_path="/amount",
        currency_path="/currency",
        high_risk=False,
        currency_exchange_rates={},
        sla_seconds=3600,
        reset_on_edit=True,
        created_at=datetime.now(tz=UTC),
    )


@patch("api.approval_flows.service")
def test_create_flow(mock_service, client, sample_approval_flow, sample_tenant_id):
    """Test creating a new approval flow."""
    mock_service.create_flow = AsyncMock(return_value=sample_approval_flow)

    payload = {
        "name": "Test Flow",
        "json_schema": {"type": "object"},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": True,
        "amount_path": "/amount",
        "currency_path": "/currency",
        "high_risk": True,
        "currency_exchange_rates": {},
        "sla_seconds": 3600,
        "reset_on_edit": True,
    }

    response = client.post(f"/tenants/{sample_tenant_id}/approval-flows/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_approval_flow.id)
    assert data["name"] == "Test Flow"
    mock_service.create_flow.assert_called_once()


@patch("api.approval_flows.service")
def test_list_flows(mock_service, client, sample_approval_flow, sample_tenant_id):
    """Test listing all approval flows for a tenant."""
    mock_service.list_flows = AsyncMock(return_value=[sample_approval_flow])

    response = client.get(f"/tenants/{sample_tenant_id}/approval-flows")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_approval_flow.id)
    assert data[0]["name"] == "Test Flow"
    mock_service.list_flows.assert_called_once()


@patch("api.approval_flows.service")
def test_get_flow(mock_service, client, sample_approval_flow, sample_tenant_id):
    """Test getting a specific approval flow."""
    mock_service.get_flow = AsyncMock(return_value=sample_approval_flow)

    response = client.get(
        f"/tenants/{sample_tenant_id}/approval-flows/{sample_approval_flow.id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_approval_flow.id)
    assert data["name"] == "Test Flow"
    mock_service.get_flow.assert_called_once()


@patch("api.approval_flows.service")
def test_get_flow_not_found(mock_service, client, sample_tenant_id):
    """Test getting a non-existent approval flow."""
    flow_id = uuid.uuid4()
    mock_service.get_flow = AsyncMock(side_effect=ApprovalFlowNotFoundError(flow_id))

    response = client.get(f"/tenants/{sample_tenant_id}/approval-flows/{flow_id}")

    assert response.status_code == 404
    data = response.json()
    assert "Approval flow not found" in data["detail"]


@patch("api.approval_flows.service")
def test_list_flow_versions(
    mock_service, client, sample_tenant_id, sample_flow_id, sample_flow_version
):
    """Test listing all versions of a flow."""
    mock_service.list_flow_versions = AsyncMock(return_value=[sample_flow_version])

    response = client.get(
        f"/tenants/{sample_tenant_id}/approval-flows/{sample_flow_id}/versions"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_flow_version.id)
    assert data[0]["version"] == 1
    mock_service.list_flow_versions.assert_called_once()


@patch("api.approval_flows.service")
def test_list_flow_versions_empty(
    mock_service, client, sample_tenant_id, sample_flow_id
):
    """Test listing versions when none exist."""
    mock_service.list_flow_versions = AsyncMock(return_value=[])

    response = client.get(
        f"/tenants/{sample_tenant_id}/approval-flows/{sample_flow_id}/versions"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@patch("api.approval_flows.service")
def test_get_flow_version(
    mock_service, client, sample_tenant_id, sample_version_id, sample_flow_version
):
    """Test getting a specific flow version."""
    mock_service.get_flow_version = AsyncMock(return_value=sample_flow_version)

    response = client.get(
        f"/tenants/{sample_tenant_id}/approval-flows/versions/{sample_version_id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_flow_version.id)
    assert data["version"] == 1
    assert data["schema_validation_enabled"] is True
    mock_service.get_flow_version.assert_called_once()


@patch("api.approval_flows.service")
def test_get_flow_version_not_found(
    mock_service, client, sample_tenant_id, sample_version_id
):
    """Test getting a non-existent flow version."""
    mock_service.get_flow_version = AsyncMock(
        side_effect=FlowVersionNotFoundError(sample_version_id)
    )

    response = client.get(
        f"/tenants/{sample_tenant_id}/approval-flows/versions/{sample_version_id}"
    )

    assert response.status_code == 404
    data = response.json()
    assert "Flow version not found" in data["detail"]


@patch("api.approval_flows.service")
def test_create_flow_multiple_versions(mock_service, client, sample_tenant_id):
    """Test creating flows with multiple versions."""
    flow1 = ApprovalFlow(
        id=uuid.uuid4(),
        tenant_id=sample_tenant_id,
        name="Flow 1",
        active_version_id=uuid.uuid4(),
        created_at=datetime.now(tz=UTC),
    )
    flow2 = ApprovalFlow(
        id=uuid.uuid4(),
        tenant_id=sample_tenant_id,
        name="Flow 2",
        active_version_id=uuid.uuid4(),
        created_at=datetime.now(tz=UTC),
    )

    mock_service.create_flow = AsyncMock(side_effect=[flow1, flow2])

    payload = {
        "name": "Flow 1",
        "json_schema": {"type": "object"},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": True,
        "amount_path": "/amount",
        "currency_path": "/currency",
        "high_risk": True,
        "currency_exchange_rates": {},
        "sla_seconds": 3600,
        "reset_on_edit": True,
    }

    response1 = client.post(
        f"/tenants/{sample_tenant_id}/approval-flows/", json=payload
    )
    assert response1.status_code == 200

    payload["name"] = "Flow 2"
    response2 = client.post(
        f"/tenants/{sample_tenant_id}/approval-flows/", json=payload
    )
    assert response2.status_code == 200


@patch("api.approval_flows.service")
def test_list_multiple_versions(mock_service, client, sample_tenant_id, sample_flow_id):
    """Test listing multiple versions of a flow."""
    versions = [
        FlowVersion(
            id=uuid.uuid4(),
            tenant_id=sample_tenant_id,
            flow_id=sample_flow_id,
            version=1,
            json_schema={"type": "object"},
            preview_schema={"type": "object"},
            schema_validation_enabled=True,
            sla_seconds=3600,
            reset_on_edit=True,
            created_at=datetime.now(tz=UTC),
        ),
        FlowVersion(
            id=uuid.uuid4(),
            tenant_id=sample_tenant_id,
            flow_id=sample_flow_id,
            version=2,
            json_schema={"type": "object", "properties": {"extra": {"type": "string"}}},
            preview_schema={"type": "object"},
            schema_validation_enabled=False,
            sla_seconds=7200,
            reset_on_edit=False,
            created_at=datetime.now(tz=UTC),
        ),
    ]

    mock_service.list_flow_versions = AsyncMock(return_value=versions)

    response = client.get(
        f"/tenants/{sample_tenant_id}/approval-flows/{sample_flow_id}/versions"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["version"] == 1
    assert data[1]["version"] == 2
    assert data[0]["schema_validation_enabled"] is True
    assert data[1]["schema_validation_enabled"] is False


@patch("api.approval_flows.service")
def test_update_flow(mock_service, client, sample_approval_flow, sample_tenant_id):
    """Test updating an approval flow."""
    mock_service.update_flow = AsyncMock(return_value=sample_approval_flow)

    payload = {
        "name": "Updated Flow",
        "json_schema": {"type": "object", "properties": {"new": {"type": "string"}}},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": False,
        "amount_path": "/amount",
        "currency_path": "/currency",
        "high_risk": True,
        "currency_exchange_rates": {},
        "sla_seconds": 7200,
        "reset_on_edit": False,
    }

    response = client.put(
        f"/tenants/{sample_tenant_id}/approval-flows/{sample_approval_flow.id}",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_approval_flow.id)
    mock_service.update_flow.assert_called_once()


@patch("api.approval_flows.service")
def test_update_flow_not_found(mock_service, client, sample_tenant_id):
    """Test updating a non-existent approval flow."""
    flow_id = uuid.uuid4()
    mock_service.update_flow = AsyncMock(side_effect=ApprovalFlowNotFoundError(flow_id))

    payload = {
        "name": "Updated Flow",
        "json_schema": {"type": "object"},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": True,
        "amount_path": "/amount",
        "currency_path": "/currency",
        "high_risk": True,
        "currency_exchange_rates": {},
        "sla_seconds": 3600,
        "reset_on_edit": True,
    }

    response = client.put(
        f"/tenants/{sample_tenant_id}/approval-flows/{flow_id}", json=payload
    )

    assert response.status_code == 404
    data = response.json()
    assert "Approval flow not found" in data["detail"]


@patch("api.approval_flows.service")
def test_update_flow_no_active_version(mock_service, client, sample_tenant_id):
    """Test updating a flow with no active version."""
    flow_id = uuid.uuid4()
    mock_service.update_flow = AsyncMock(side_effect=NoActiveVersionError(flow_id))

    payload = {
        "name": "Updated Flow",
        "json_schema": {"type": "object"},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": True,
        "amount_path": "/amount",
        "currency_path": "/currency",
        "high_risk": True,
        "currency_exchange_rates": {},
        "sla_seconds": 3600,
        "reset_on_edit": True,
    }

    response = client.put(
        f"/tenants/{sample_tenant_id}/approval-flows/{flow_id}", json=payload
    )

    assert response.status_code == 404
    data = response.json()
    assert "active version" in data["detail"]


@patch("api.approval_flows.service")
def test_update_flow_active_version_not_found(mock_service, client, sample_tenant_id):
    """Test updating a flow when active version is not found."""
    flow_id = uuid.uuid4()
    version_id = uuid.uuid4()
    mock_service.update_flow = AsyncMock(
        side_effect=FlowVersionNotFoundError(version_id)
    )

    payload = {
        "name": "Updated Flow",
        "json_schema": {"type": "object"},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": True,
        "amount_path": "/amount",
        "currency_path": "/currency",
        "high_risk": True,
        "currency_exchange_rates": {},
        "sla_seconds": 3600,
        "reset_on_edit": True,
    }

    response = client.put(
        f"/tenants/{sample_tenant_id}/approval-flows/{flow_id}", json=payload
    )

    assert response.status_code == 404
    data = response.json()
    assert "Active flow version not found" in data["detail"]


@patch("api.approval_flows.service")
def test_create_flow_with_financial_fields(
    mock_service, client, sample_approval_flow, sample_tenant_id
):
    """Test creating a flow with financial fields."""
    mock_service.create_flow = AsyncMock(return_value=sample_approval_flow)

    payload = {
        "name": "Financial Flow",
        "json_schema": {"type": "object", "properties": {"amount": {"type": "number"}}},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": True,
        "amount_path": "/amount",
        "currency_path": "/currency",
        "high_risk": True,
        "currency_exchange_rates": {"USD": 1.0, "EUR": 0.92},
        "sla_seconds": 3600,
        "reset_on_edit": True,
    }

    response = client.post(f"/tenants/{sample_tenant_id}/approval-flows/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_approval_flow.id)
    mock_service.create_flow.assert_called_once()
    call_args = mock_service.create_flow.call_args
    assert call_args.kwargs["amount_path"] == "/amount"
    assert call_args.kwargs["currency_path"] == "/currency"
    assert call_args.kwargs["high_risk"] is True
    assert call_args.kwargs["currency_exchange_rates"] == {"USD": 1.0, "EUR": 0.92}


@patch("api.approval_flows.service")
def test_update_flow_financial_fields(
    mock_service, client, sample_approval_flow, sample_tenant_id
):
    """Test updating a flow with financial fields."""
    mock_service.update_flow = AsyncMock(return_value=sample_approval_flow)

    payload = {
        "json_schema": {"type": "object", "properties": {"amount": {"type": "number"}}},
        "preview_schema": {"type": "object"},
        "schema_validation_enabled": True,
        "amount_path": "/request/amount",
        "currency_path": "/request/currency",
        "high_risk": True,
        "currency_exchange_rates": {"USD": 1.0, "EUR": 0.92, "GBP": 0.80},
        "sla_seconds": 7200,
        "reset_on_edit": False,
    }

    response = client.put(
        f"/tenants/{sample_tenant_id}/approval-flows/{sample_approval_flow.id}",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_approval_flow.id)
    mock_service.update_flow.assert_called_once()
    call_args = mock_service.update_flow.call_args
    assert call_args.kwargs["amount_path"] == "/request/amount"
    assert call_args.kwargs["currency_path"] == "/request/currency"
    assert call_args.kwargs["high_risk"] is True
    assert call_args.kwargs["currency_exchange_rates"] == {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.80,
    }
    assert call_args.kwargs["sla_seconds"] == 7200
    assert call_args.kwargs["reset_on_edit"] is False
