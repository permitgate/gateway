# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

from enum import StrEnum


class UserRole(StrEnum):
    """Enum for user role."""

    ADMINISTRATOR = "administrator"
    REVIEWER = "reviewer"
