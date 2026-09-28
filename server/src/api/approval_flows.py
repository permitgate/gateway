# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schema.schemas import (
    ApprovalFlowCreate,
    ApprovalFlowResponse,
    ApprovalFlowUpdate,
    ApprovalFlowVersionResponse,
    ApprovalStepResponse,
)
from db import get_session
from service.approval_flows_service import ApprovalFlowsService
from service.approval_steps_service import ApprovalStepsService
from service.exceptions import (
    ApprovalFlowNotFoundError,
    FlowVersionNotFoundError,
    InvalidApprovalStepError,
    InvalidFlowSchemaError,
    NoActiveVersionError,
)

_ERROR_RESPONSE = {
    "description": "Error response",
    "content": {
        "application/json": {
            "schema": {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    },
}

router = APIRouter(
    prefix="/tenants/{tenant_id}/approval-flows", tags=["Approval Flows"]
)
service = ApprovalFlowsService()
steps_service = ApprovalStepsService()


@router.post(
    "/",
    response_model=ApprovalFlowResponse,
    responses={
        200: {"description": "Approval flow created successfully"},
        400: _ERROR_RESPONSE,
    },
)
async def create_flow(
    tenant_id: uuid.UUID,
    flow: ApprovalFlowCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApprovalFlowResponse:
    """Create a new approval flow for a tenant.

    Returns 200 with the created ApprovalFlow object."""
    try:
        created_flow = await service.create_flow(
            session=session,
            tenant_id=tenant_id,
            name=flow.name,
            json_schema=flow.json_schema,
            preview_schema=flow.preview_schema,
            schema_validation_enabled=flow.schema_validation_enabled,
            amount_path=flow.amount_path,
            currency_path=flow.currency_path,
            high_risk=flow.high_risk,
            currency_exchange_rates=flow.currency_exchange_rates,
            sla_seconds=flow.sla_seconds,
            reset_on_edit=flow.reset_on_edit,
            steps=flow.steps,
        )
        return ApprovalFlowResponse.model_validate(created_flow, from_attributes=True)
    except InvalidFlowSchemaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except InvalidApprovalStepError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/",
    response_model=list[ApprovalFlowResponse],
    responses={
        200: {"description": "List of all approval flows for a tenant"},
    },
)
async def list_flows(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[ApprovalFlowResponse]:
    """List all approval flows for a specific tenant.

    Returns 200 with a list of ApprovalFlow objects for the tenant."""
    flows = await service.list_flows(session, tenant_id)
    return [
        ApprovalFlowResponse.model_validate(flow, from_attributes=True)
        for flow in flows
    ]


@router.get(
    "/{flow_id}",
    response_model=ApprovalFlowResponse,
    responses={
        200: {"description": "Approval flow retrieved successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def get_flow(
    tenant_id: uuid.UUID,
    flow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApprovalFlowResponse:
    """Get a specific approval flow by ID for a tenant.

    Returns 200 with the ApprovalFlow object or 404 if not found."""
    try:
        flow = await service.get_flow(session, tenant_id, flow_id)
        return ApprovalFlowResponse.model_validate(flow, from_attributes=True)
    except ApprovalFlowNotFoundError:
        raise HTTPException(status_code=404, detail="Approval flow not found")


@router.put(
    "/{flow_id}",
    response_model=ApprovalFlowResponse,
    responses={
        200: {"description": "Approval flow updated successfully"},
        400: _ERROR_RESPONSE,
        404: _ERROR_RESPONSE,
    },
)
async def update_flow(
    tenant_id: uuid.UUID,
    flow_id: uuid.UUID,
    flow: ApprovalFlowUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApprovalFlowResponse:
    """Update an approval flow by creating a new version for a tenant.

    Returns 200 with the updated ApprovalFlow object.
    Returns 400 if the schema is invalid.
    Returns 404 if the flow is not found, has no active version, or active version is not found."""
    try:
        updated_flow = await service.update_flow(
            session=session,
            tenant_id=tenant_id,
            flow_id=flow_id,
            json_schema=flow.json_schema,
            preview_schema=flow.preview_schema,
            schema_validation_enabled=flow.schema_validation_enabled,
            amount_path=flow.amount_path,
            currency_path=flow.currency_path,
            high_risk=flow.high_risk,
            currency_exchange_rates=flow.currency_exchange_rates,
            sla_seconds=flow.sla_seconds,
            reset_on_edit=flow.reset_on_edit,
            steps=flow.steps,
        )
        return ApprovalFlowResponse.model_validate(updated_flow, from_attributes=True)
    except InvalidFlowSchemaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except InvalidApprovalStepError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ApprovalFlowNotFoundError:
        raise HTTPException(status_code=404, detail="Approval flow not found")
    except NoActiveVersionError:
        raise HTTPException(
            status_code=404, detail="Approval flow has no active version"
        )
    except FlowVersionNotFoundError:
        raise HTTPException(status_code=404, detail="Active flow version not found")


@router.get(
    "/{flow_id}/versions",
    response_model=list[ApprovalFlowVersionResponse],
    responses={
        200: {"description": "List of all versions for the approval flow"},
    },
)
async def list_flow_versions(
    tenant_id: uuid.UUID,
    flow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[ApprovalFlowVersionResponse]:
    """List all versions of an approval flow for a tenant.

    Returns 200 with a list of FlowVersion objects ordered by version number."""
    versions = await service.list_flow_versions(session, tenant_id, flow_id)
    return [
        ApprovalFlowVersionResponse.model_validate(version, from_attributes=True)
        for version in versions
    ]


@router.get(
    "/versions/{version_id}",
    response_model=ApprovalFlowVersionResponse,
    responses={
        200: {"description": "Flow version retrieved successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def get_flow_version(
    tenant_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApprovalFlowVersionResponse:
    """Get a specific approval flow version by ID for a tenant.

    Returns 200 with the FlowVersion object or 404 if not found."""
    try:
        version = await service.get_flow_version(session, tenant_id, version_id)
        return ApprovalFlowVersionResponse.model_validate(version, from_attributes=True)
    except FlowVersionNotFoundError:
        raise HTTPException(status_code=404, detail="Flow version not found")


@router.get(
    "/versions/{version_id}/steps",
    response_model=list[ApprovalStepResponse],
    responses={200: {"description": "List of all steps for the flow version"}},
)
async def list_flow_version_steps(
    tenant_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[ApprovalStepResponse]:
    """List all approval steps for a flow version, ordered by step_order."""
    steps = await steps_service.list_steps_for_flow_version(
        session, tenant_id, version_id
    )
    return [ApprovalStepResponse.model_validate(s, from_attributes=True) for s in steps]
