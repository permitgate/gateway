# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from model.user_role import UserRole


class ApprovalStepInput(BaseModel):
    """Schema for approval step input during creation."""

    name: str
    target_group_id: uuid.UUID | None = None
    target_user_id: uuid.UUID | None = None
    editable_paths: list[str] = Field(default_factory=list)
    amount_limit_minor_units: int | None = Field(gt=0, default=None)
    currency: str | None = None
    required_role: UserRole | None = None
    action_type: str | None = None

    @model_validator(mode="after")
    def check_exactly_one_approval_target(self) -> "ApprovalStepInput":
        """Ensure exactly one of target_group_id or target_user_id is set."""
        has_group = self.target_group_id is not None
        has_user = self.target_user_id is not None
        if (has_group and has_user) or (not has_group and not has_user):
            msg = "Exactly one of target_group_id or target_user_id must be set"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def check_amount_currency_bound(self) -> "ApprovalStepInput":
        """Ensure amount_limit_minor_units and currency are both set or both None."""
        has_amount = self.amount_limit_minor_units is not None
        has_currency = self.currency is not None
        if has_amount != has_currency:
            msg = (
                "amount_limit_minor_units and currency must both be set or both be None"
            )
            raise ValueError(msg)
        return self


class ApprovalStep(BaseModel):
    """Schema for approval step entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
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
