# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .user_role import UserRole


class User(BaseModel):
    """Schema for user entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: UserRole
    slack_user_id: str | None
    teams_user_id: str | None
    telegram_user_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
