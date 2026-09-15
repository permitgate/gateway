# Copyright (C) 2026, Evgenii Romanov.
# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

from enum import StrEnum


class ExecutionState(StrEnum):
    """Enum for execution state."""

    NOT_STARTED = "not_started"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"
