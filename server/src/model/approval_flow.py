# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApprovalFlow(BaseModel):
    """Schema for approval flow entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    active_version_id: uuid.UUID | None
    created_at: datetime


class ApprovalFlowVersion(BaseModel):
    """Schema for approval flow version entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
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
