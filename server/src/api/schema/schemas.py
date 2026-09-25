# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from model import ApprovalStepInput, UserRole


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

    @field_validator("email", mode="before")
    @classmethod
    def validate_email_not_null(cls, value: Any) -> Any:
        """Reject explicit null email while allowing omission for partial updates."""
        if value is None:
            msg = "email may be omitted, but cannot be null"
            raise ValueError(msg)
        return value


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
    amount_path: str | None = None
    currency_path: str | None = None
    high_risk: bool = False
    currency_exchange_rates: dict = Field(default_factory=dict)
    sla_seconds: int = Field(gt=0)
    reset_on_edit: bool
    steps: list[ApprovalStepInput] = Field(min_length=1)


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
    amount_path: str | None
    currency_path: str | None
    high_risk: bool
    currency_exchange_rates: dict
    sla_seconds: int
    reset_on_edit: bool
    created_at: datetime


class ApprovalStepResponse(BaseModel):
    """Schema for approval step response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    flow_version_id: uuid.UUID
    step_order: int
    name: str
    target_group_id: uuid.UUID | None
    target_user_id: uuid.UUID | None
    editable_paths: list[str]
    amount_limit_minor_units: int | None
    currency: str | None
    required_role: UserRole | None
    action_type: str | None
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
    priority: int = Field(default=0, ge=0)


class GroupMembershipResponse(BaseModel):
    """Schema for group membership response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    priority: int
    is_active: bool
    created_at: datetime
