# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid


class ApprovalFlowNotFoundError(Exception):
    """Raised when an approval flow is not found."""

    def __init__(self, flow_id: uuid.UUID):
        self.flow_id = flow_id
        super().__init__(f"Approval flow with ID {flow_id} not found")


class NoActiveVersionError(Exception):
    """Raised when a flow doesn't have active version defined."""

    def __init__(self, version_id: uuid.UUID):
        self.version_id = version_id
        super().__init__(f"Flow with ID {version_id} doesn't have active version")


class FlowVersionNotFoundError(Exception):
    """Raised when a flow version is not found."""

    def __init__(self, version_id: uuid.UUID):
        self.version_id = version_id
        super().__init__(f"Flow version with ID {version_id} not found")
