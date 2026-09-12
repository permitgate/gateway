# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApprovalFlowUpdate(BaseModel):
    """Schema for updating an approval flow."""

    json_schema: dict
    preview_schema: dict
    schema_validation_enabled: bool
    sla_seconds: int = Field(gt=0)
    reset_on_edit: bool


class ApprovalFlowCreate(ApprovalFlowUpdate):
    """Schema for creating an approval flow."""

    name: str


class ApprovalFlowResponse(BaseModel):
    """Schema for approval flow response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    active_version_id: uuid.UUID
    created_at: datetime


class ApprovalFlowVersionResponse(BaseModel):
    """Schema for approval flow version response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    flow_id: uuid.UUID
    version: int
    json_schema: dict
    preview_schema: dict
    schema_validation_enabled: bool
    sla_seconds: int
    reset_on_edit: bool
    created_at: datetime
