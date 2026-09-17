# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from model import UserRole


class UserCreate(BaseModel):
    """Schema for creating a user."""

    email: EmailStr
    role: UserRole = UserRole.REVIEWER
    slack_user_id: str | None = None
    teams_user_id: str | None = None
    telegram_user_id: str | None = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    role: UserRole | None = None
    slack_user_id: str | None = None
    teams_user_id: str | None = None
    telegram_user_id: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    slack_user_id: str | None
    teams_user_id: str | None
    telegram_user_id: str | None
    is_active: bool
    created_at: datetime


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
    active_version_id: uuid.UUID | None
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


class GroupCreate(BaseModel):
    """Schema for creating a reviewer group."""

    name: str
    user_ids: list[uuid.UUID] = Field(default_factory=list)


class GroupResponse(BaseModel):
    """Schema for reviewer group response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class GroupMembershipCreate(BaseModel):
    """Schema for adding a user to a group."""

    user_id: uuid.UUID
    priority: int = 0


class GroupMembershipResponse(BaseModel):
    """Schema for group membership response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    priority: int
    is_active: bool
    created_at: datetime
